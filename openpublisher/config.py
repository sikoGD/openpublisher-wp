import json
from pathlib import Path
from urllib.parse import urlsplit


def https_url(value):
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('A clean HTTPS URL is required')
    if parsed.port is not None and not (1 <= parsed.port <= 65535):
        raise ValueError('Invalid port')
    return value


def load_config(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    site = data.get('wordpress', {})
    base = site.get('api_base', '')
    https_url(base)
    from urllib.parse import urlsplit
    from re import fullmatch
    api_path = urlsplit(base.rstrip('/')).path
    standard = api_path.endswith('/wp/v2')
    wordpress_com = bool(fullmatch(r'/wp/v2/sites/[a-zA-Z0-9._-]+', api_path)) and urlsplit(base).hostname == 'public-api.wordpress.com'
    if not (standard or wordpress_com):
        raise ValueError('api_base must end with /wp/v2 or /wp/v2/sites/{site_id} on WordPress.com')
    auth_mode = site.get('auth_mode', 'application_password')
    if auth_mode not in ('application_password', 'wordpress_com_oauth', 'bearer'):
        raise ValueError('wordpress.auth_mode must be application_password, wordpress_com_oauth or bearer')
    if wordpress_com and auth_mode == 'application_password':
        raise ValueError('WordPress.com public API proxy requires wordpress_com_oauth or bearer')
    feeds = data.get('feeds', [])
    if not isinstance(feeds, list) or not feeds:
        raise ValueError('At least one RSS/Atom feed is required')
    for item in feeds:
        if not isinstance(item, dict) or not item.get('name'):
            raise ValueError('Every feed needs a name and URL')
        https_url(item['url'])
    editorial = data.get('editorial', {})
    if not isinstance(editorial.get('lookback_days', 10), int) or not 1 <= editorial.get('lookback_days', 10) <= 365:
        raise ValueError('lookback_days must be between 1 and 365')
    provider = editorial.get('provider', 'template')
    if provider not in ('template', 'openai', 'external_json'):
        raise ValueError('editorial.provider must be template, openai or external_json')
    if provider == 'external_json':
        https_url(editorial.get('external_json_url', ''))
    if not isinstance(editorial.get('max_cost_usd', 0), (int, float)) or editorial.get('max_cost_usd', 0) < 0:
        raise ValueError('editorial.max_cost_usd cannot be negative')
    if not isinstance(editorial.get('max_output_tokens', 1200), int) or not 1 <= editorial.get('max_output_tokens', 1200) <= 8000:
        raise ValueError('editorial.max_output_tokens must be between 1 and 8000')
    if editorial.get('source_quality_policy', 'review_all') not in ('review_all', 'allowlist'):
        raise ValueError('source_quality_policy must be review_all or allowlist')
    if editorial.get('source_quality_policy') == 'allowlist':
        hosts = editorial.get('allowed_source_hosts', [])
        if not isinstance(hosts, list) or not hosts or any(not isinstance(h, str) or not h for h in hosts):
            raise ValueError('allowlist policy requires allowed_source_hosts')
        for feed in feeds:
            if urlsplit(feed['url']).hostname not in hosts:
                raise ValueError('Feed host is not included in editorial.allowed_source_hosts')
    if not (1 <= int(editorial.get('max_sources', 12)) <= 50):
        raise ValueError('max_sources must be between 1 and 50')
    return data
