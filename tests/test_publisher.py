import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from openpublisher.config import https_url, load_config
from openpublisher.editorial import article_validation, template_draft
from openpublisher.feeds import parse_feed
from openpublisher.wordpress import similarity, publish
from openpublisher.wordpress import _request, _existing_posts
from urllib.error import HTTPError, URLError


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.config = {'wordpress': {'api_base': 'https://blog.example/wp-json/wp/v2',
                                     'auth_mode': 'application_password'},
                       'feeds': [{'name': 'Demo', 'url': 'https://example.org/feed.xml'}],
                       'editorial': {'provider': 'template'}}
        self.source = {'sources': [{'url': 'https://example.org/story', 'title': 'The Example Article',
                                    'publisher': 'Demo', 'summary': 'A sample',
                                    'published_at': '2026-11-02T01:00:00+00:00'}]}

    def test_config_valid(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'config.json'; p.write_text(json.dumps(self.config))
            self.assertIn('feeds', load_config(p))

    def test_wordpress_com_config(self):
        self.config['wordpress']['api_base'] = 'https://public-api.wordpress.com/wp/v2/sites/12345'
        self.config['wordpress']['auth_mode'] = 'wordpress_com_oauth'
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'config.json'; p.write_text(json.dumps(self.config))
            self.assertIn('wordpress', load_config(p))

    def test_url_validation(self):
        with self.assertRaises(ValueError):
            https_url('http://example.org')
        with self.assertRaises(ValueError):
            https_url('https://username:password@example.org/')

    def test_template_is_unreviewed(self):
        article = template_draft(self.source)
        self.assertFalse(article['reviewed'])
        self.assertTrue(article_validation(article))
        with self.assertRaises(ValueError):
            article_validation(article, require_review=True)

    def test_dry_run_never_calls_wordpress(self):
        article = template_draft(self.source)
        with patch('openpublisher.wordpress._authorization', side_effect=AssertionError('unexpected network/auth')):
            outcome = publish(article, self.config, live=False, status='publish')
        self.assertTrue(outcome['dry_run'])

    def test_source_is_required(self):
        article = template_draft(self.source); article['primary_source_url'] = 'https://fake.org/x'
        with self.assertRaises(ValueError):
            article_validation(article)

    def test_duplicate_title(self):
        self.assertGreaterEqual(similarity('OpenSource Games Festival', 'OpenSource Games Festival!'), 0.72)

    def test_parse_rss(self):
        xml = b'<rss version="2.0"><channel><item><title>Testing</title><link>https://example.org/1</link><pubDate>Mon, 02 Nov 2026 10:00:00 GMT</pubDate><description>Short</description></item></channel></rss>'
        from datetime import datetime, timezone
        leads = parse_feed(xml, 'Demo', now=datetime(2026,11,2,11,tzinfo=timezone.utc))
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]['title'], 'Testing')

    def test_duplicate_prevents_post(self):
        article = template_draft(self.source)
        article['reviewed'] = True
        with patch('openpublisher.wordpress._authorization', return_value={'Authorization': 'TEST'}), \
             patch('openpublisher.wordpress._existing_posts', return_value=[{'title': {'rendered': article['title']}, 'content': {'rendered': ''}}]), \
             patch('openpublisher.wordpress._request', side_effect=AssertionError('should not post')):
            with self.assertRaisesRegex(RuntimeError, 'duplicate'):
                publish(article, self.config, live=True)

    def test_wordpress_com_rejects_application_password(self):
        self.config['wordpress'] = {'api_base': 'https://public-api.wordpress.com/wp/v2/sites/123',
                                    'auth_mode': 'application_password'}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'config.json'; path.write_text(json.dumps(self.config))
            with self.assertRaisesRegex(ValueError, 'requires'):
                load_config(path)

    def test_api_error_does_not_expose_response_body(self):
        class Opener:
            def open(self, req, timeout):
                raise HTTPError(req.full_url, 401, 'Unauthorized', {}, None)
        with patch('openpublisher.wordpress.build_opener', return_value=Opener()):
            with self.assertRaisesRegex(RuntimeError, 'HTTP error 401') as caught:
                _request('https://blog.example/wp-json/wp/v2/posts', headers={'Authorization': 'Bearer secret'})
            self.assertNotIn('secret', str(caught.exception))

    def test_permission_error_is_sanitized(self):
        class Opener:
            def open(self, req, timeout): raise HTTPError(req.full_url, 403, 'Forbidden', {}, None)
        with patch('openpublisher.wordpress.build_opener', return_value=Opener()):
            with self.assertRaisesRegex(RuntimeError, 'HTTP error 403'):
                _request('https://blog.example/wp-json/wp/v2/posts')

    def test_redirect_handler_rejects_redirects(self):
        from openpublisher.wordpress import _NoRedirect
        handler = _NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, 'Found', {}, 'https://other.example/'))

    def test_wordpress_com_oauth_exchange(self):
        from openpublisher.wordpress import _authorization
        config = {'wordpress': {'api_base': 'https://public-api.wordpress.com/wp/v2/sites/123',
                                'auth_mode': 'wordpress_com_oauth'}}
        env = {'WP_CLIENT_ID': 'id', 'WP_CLIENT_SECRET': 'secret', 'WP_USERNAME': 'user', 'WP_APP_PASSWORD': 'pass'}
        with patch.dict('os.environ', env, clear=True), patch('openpublisher.wordpress._request',
                return_value=({'access_token': 'token-example'}, {})) as mocked:
            self.assertEqual(_authorization(config), {'Authorization': 'Bearer token-example'})
            self.assertEqual(mocked.call_args.args[0], 'https://public-api.wordpress.com/oauth2/token')

    def test_pagination_walks_all_pages(self):
        page1 = [{'id': 1}]; page2 = [{'id': 2}]
        with patch('openpublisher.wordpress._request', side_effect=[(page1, {'X-WP-TotalPages': '2'}),
                                                                  (page2, {'X-WP-TotalPages': '2'})]) as mocked:
            self.assertEqual(_existing_posts('https://blog.example/wp-json/wp/v2', {}), page1 + page2)
            self.assertEqual(mocked.call_count, 2)

    def test_timeout_is_sanitized(self):
        class Opener:
            def open(self, req, timeout): raise URLError('timed out')
        with patch('openpublisher.wordpress.build_opener', return_value=Opener()):
            with self.assertRaisesRegex(RuntimeError, 'network or TLS') as caught:
                _request('https://blog.example/wp-json/wp/v2/posts')
            self.assertNotIn('timed out', str(caught.exception))

    def test_missing_pagination_header_blocks_duplicate_check(self):
        with patch('openpublisher.wordpress._request', return_value=([], {})):
            with self.assertRaisesRegex(RuntimeError, 'pagination metadata'):
                _existing_posts('https://blog.example/wp-json/wp/v2', {})

    def test_source_allowlist_filters_briefing(self):
        from openpublisher.editorial import create_draft
        config = {**self.config, 'editorial': {'provider': 'template', 'source_quality_policy': 'allowlist',
                                               'allowed_source_hosts': ['example.org']}}
        article = create_draft({'sources': self.source['sources'] + [{'url': 'https://bad.example/x',
            'title': 'Bad lead', 'publisher': 'bad', 'summary': '', 'published_at': '2026-11-02'}]}, config)
        self.assertTrue(all('example.org' in url for url in article['sources']))

if __name__ == '__main__':
    unittest.main()
