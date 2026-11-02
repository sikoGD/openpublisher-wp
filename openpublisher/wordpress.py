"""WordPress.org REST/basic app password or WordPress.com OAuth client."""
import base64
import json
import os
import re
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from .config import https_url
from .editorial import article_validation


def similarity(first, second):
    def words(title):
        return set(x for x in re.findall(r'[\w\d]{3,}', title.casefold())
                   if x not in {'the', 'and', 'for', 'from', 'with', 'this', 'that'})
    a, b = words(first), words(second)
    token = len(a & b) / len(a | b) if a and b else 0.0
    def grams(value):
        value = '  ' + re.sub(r'\W+', ' ', value.casefold()).strip() + '  '
        return {value[i:i+3] for i in range(max(0, len(value)-2))}
    ga, gb = grams(first), grams(second)
    ngram = len(ga & gb) / len(ga | gb) if ga and gb else 0.0
    # A conservative heuristic; it can flag related stories and never proves uniqueness.
    return max(token, 0.65 * token + 0.35 * ngram)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _request(url, *, method='GET', payload=None, headers=None, form=False):
    https_url(url)
    data = None
    req_headers = {'User-Agent': 'OpenPublisherWP/0.1', 'Accept': 'application/json', **(headers or {})}
    if payload is not None:
        data = (urlencode(payload).encode('utf-8') if form else json.dumps(payload).encode('utf-8'))
        req_headers['Content-Type'] = ('application/x-www-form-urlencoded' if form else 'application/json')
    req = Request(url, data=data, method=method, headers=req_headers)
    try:
        # Reject redirects before urllib has any opportunity to forward credentials.
        with build_opener(_NoRedirect()).open(req, timeout=30) as resp:
            body = resp.read(2_000_000)
            return json.loads(body), dict(resp.headers)
    except HTTPError as exc:
        # Avoid exposing response bodies which may reflect tokens or secrets.
        raise RuntimeError(f'WordPress API HTTP error {exc.code}') from None
    except URLError:
        raise RuntimeError('WordPress API network or TLS error') from None


def _authorization(config):
    site = config['wordpress']
    mode = site.get('auth_mode', 'application_password')
    if mode == 'bearer':
        token = os.environ.get('WP_BEARER_TOKEN')
        if not token:
            raise RuntimeError('WP_BEARER_TOKEN missing')
        return {'Authorization': f'Bearer {token}'}
    if mode == 'application_password':
        if 'public-api.wordpress.com' in site['api_base']:
            raise ValueError('Use wordpress_com_oauth or bearer for the WordPress.com public API')
        username, secret = os.environ.get('WP_USERNAME'), os.environ.get('WP_APP_PASSWORD')
        if not username or not secret:
            raise RuntimeError('WP_USERNAME and WP_APP_PASSWORD must be configured')
        encoded = base64.b64encode((username + ':' + secret).encode()).decode()
        return {'Authorization': f'Basic {encoded}'}
    if mode == 'wordpress_com_oauth':
        required = ('WP_CLIENT_ID', 'WP_CLIENT_SECRET', 'WP_USERNAME', 'WP_APP_PASSWORD')
        if not all(os.environ.get(x) for x in required):
            raise RuntimeError('WordPress.com OAuth requires four WP_* environment variables')
        credentials = {
            'grant_type': 'password',
            'client_id': os.environ['WP_CLIENT_ID'],
            'client_secret': os.environ['WP_CLIENT_SECRET'],
            'username': os.environ['WP_USERNAME'],
            'password': os.environ['WP_APP_PASSWORD']
        }
        data, _ = _request('https://public-api.wordpress.com/oauth2/token', method='POST',
                           payload=credentials, form=True)
        token = data.get('access_token')
        if not token:
            raise RuntimeError('WordPress.com token exchange returned no token')
        return {'Authorization': f'Bearer {token}'}
    raise ValueError('Unknown auth_mode')


def _existing_posts(api, headers):
    posts = []
    for page in range(1, 11):
        qs = urlencode({'per_page': 100, 'page': page, 'context': 'edit', 'status': 'any'})
        batch, meta = _request(f'{api}/posts?{qs}', headers=headers)
        if not isinstance(batch, list):
            raise RuntimeError('Invalid posts API response; refusing to proceed')
        posts.extend(batch)
        try:
            pages = int(next((v for k, v in meta.items() if k.lower() == 'x-wp-totalpages'), ''))
        except (ValueError, TypeError):
            raise RuntimeError('WordPress pagination metadata missing; refusing incomplete duplicate check') from None
        if pages > 10:
            raise RuntimeError('Over 1000 posts: duplicate check limit reached; refusing to publish')
        if not batch or page >= pages:
            break
    return posts


def publish(article, config, *, live=False, status='draft'):
    article_validation(article, require_review=live)
    if status not in ('draft', 'publish'):
        raise ValueError('Only draft and publish statuses supported')
    if not live:
        return {'dry_run': True, 'status_requested': status, 'notice': 'No WordPress network action performed'}
    api = https_url(config['wordpress']['api_base']).rstrip('/')
    headers = _authorization(config)
    existing = _existing_posts(api, headers)
    for prior in existing:
        old_title = unescape(re.sub(r'<[^>]*>', '', prior.get('title', {}).get('rendered', '')))
        if similarity(article['title'], old_title) >= 0.72:
            raise RuntimeError('Similar article title already exists; refusing duplicate')
        if article['primary_source_url'] in prior.get('content', {}).get('rendered', ''):
            raise RuntimeError('Primary source already exists in another article; refusing duplicate')
    posted, _ = _request(f'{api}/posts', method='POST', headers=headers,
                         payload={'title': article['title'], 'excerpt': article['excerpt'],
                                  'content': article['content_html'], 'status': status})
    return {'dry_run': False, 'post_id': posted.get('id'), 'url': posted.get('link'),
            'status': status}
