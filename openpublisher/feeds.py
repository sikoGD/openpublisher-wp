"""Small standard-library RSS/Atom collector with no web scraping."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit
from xml.etree import ElementTree
from .config import https_url

_MAX_FEED = 3_000_000


def _strip_html(value):
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]*>', ' ', value or ''))).strip()


def _date(value):
    if not value:
        return None
    try:
        d = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)


def parse_feed(xml_bytes, name, max_age_days=10, now=None):
    if len(xml_bytes) > _MAX_FEED:
        raise ValueError('Feed is too large')
    root = ElementTree.fromstring(xml_bytes)
    now = now or datetime.now(timezone.utc)
    oldest = now - timedelta(days=max_age_days)
    out = []
    if root.tag.lower().endswith('rss') or root.find('channel') is not None:
        for item in root.findall('./channel/item'):
            link = (item.findtext('link') or '').strip()
            title = _strip_html(item.findtext('title'))
            summary = _strip_html(item.findtext('description'))
            when = _date(item.findtext('pubDate'))
            if link.startswith('https://') and title and when and when >= oldest:
                out.append({'publisher': name, 'title': title[:250], 'url': link,
                            'summary': summary[:1200], 'published_at': when.isoformat()})
    else:
        ns = '{http://www.w3.org/2005/Atom}'
        for entry in root.findall(ns + 'entry'):
            title = _strip_html(entry.findtext(ns + 'title'))
            summary = _strip_html(entry.findtext(ns + 'summary') or entry.findtext(ns + 'content'))
            when = _date(entry.findtext(ns + 'published') or entry.findtext(ns + 'updated'))
            links = [x.attrib.get('href', '') for x in entry.findall(ns + 'link') if x.attrib.get('rel', 'alternate') == 'alternate']
            link = next((x for x in links if x.startswith('https://')), '')
            if link and title and when and when >= oldest:
                out.append({'publisher': name, 'title': title[:250], 'url': link,
                            'summary': summary[:1200], 'published_at': when.isoformat()})
    return out


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def collect(config):
    seen, sources, errors = set(), [], []
    editorial = config.get('editorial', {})
    for feed in config['feeds']:
        try:
            https_url(feed['url'])
            req = Request(feed['url'], headers={'User-Agent': 'OpenPublisherWP/0.1'})
            # Use urllib TLS verification; forbid HTTP downgrade and unexpected host redirects.
            with build_opener(_NoRedirect()).open(req, timeout=20) as resp:
                xml = resp.read(_MAX_FEED + 1)
            for item in parse_feed(xml, feed['name'], editorial.get('lookback_days', 10)):
                if item['url'] not in seen:
                    seen.add(item['url']); sources.append(item)
        except Exception as exc:
            # Avoid printing remote error response bodies or any secret-containing URLs.
            errors.append({'feed': feed['name'], 'error_type': type(exc).__name__})
    sources.sort(key=lambda x: x['published_at'], reverse=True)
    return {'sources': sources[:editorial.get('max_sources', 12)], 'feed_errors': errors}
