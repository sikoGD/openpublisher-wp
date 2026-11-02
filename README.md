# Open Publisher for WordPress � OSS starter v0.1

Blog-independent adaptation of the **architecture and safeguards** developed for the private ExtraSouls Publisher project. Original implementation, with no ExtraSouls site ID, feeds, credentials or proprietary assets. MIT-licensed.

This is a **prototype for maintainers**, not a hosted service. Each publisher runs it on their own machine or GitHub Actions and controls their own configuration, OpenAI costs and WordPress credentials.

## Already implemented

- Generic RSS and Atom source discovery, basic recency filtering, source deduplication, HTTPS-only feed URLs, and error summaries.
- Reusable **editorial research outline**, or **optional OpenAI Responses API draft generation** (`pip install -r requirements-optional.txt`).
- Every generated article defaults to **unreviewed**. Human fact-check and editorial approval are required for live posting.
- WordPress REST post creation using **self-hosted Application Password Basic Auth**, **WordPress.com OAuth2 token exchange**, or an existing **Bearer token**.
- Duplicate checks against existing posts using title similarity and reused primary source URL. Publication refuses to proceed if these checks fail.
- Default dry-run mode; live writing requires explicit `--live`, verified source link, `reviewed: true`, and a chosen post status (`draft` by default).
- Standard-library only for template mode; optional OpenAI SDK for AI drafts. Unit tests and GitHub Actions checks included.
- Editorial queue (`queue`) and explicit human approval (`approve`) commands. Approval records a reviewer but still does not publish.
- Optional external JSON generator endpoint, with HTTPS, redirect refusal, source allow-list checks and a cross-host opt-in.
- Scheduled GitHub workflow produces an unreviewed artifact for human review. It never calls WordPress publishing endpoints.

## Quick start

Python 3.10+:

```bash
cp config.example.json config.json
# Edit config.json: WordPress API URL and RSS feeds. Secrets go in env vars, NOT config.json.
python -m openpublisher collect
python -m openpublisher generate
python -m openpublisher validate
python -m openpublisher publish
```

The last command is **dry-run** and performs no WordPress network call. You may test generation without a live site using:

```bash
python -m openpublisher generate --sources examples/synthetic-sources.json
```

If you choose `provider: "openai"`, install the optional dependency and set `OPENAI_API_KEY`. This uses your own paid API credits and **does not** come with a ChatGPT Pro plan.

**Only after independently fact-checking and editing** `output/article.json`, changing its `reviewed` flag to `true`, and configuring WordPress auth:

```bash
python -m openpublisher publish --live --status draft
# Publishing immediately to the public site requires an additional explicit choice:
python -m openpublisher publish --live --status publish
```

## Editorial review and scheduled drafts

`python -m openpublisher queue --article output/article.json` stores an unreviewed entry in `output/review-queue.json`. After fact-checking and editing the article, explicitly record approval with `python -m openpublisher approve --article output/article.json --reviewer "Your name"`. Approval only sets the reviewed marker; posting remains a separate explicit command and defaults to WordPress draft status. Treat the queue as local editorial data and do not commit it.

The scheduled workflow requires a public-safe `config.json` with feeds that you are authorized to use. Its run stops before any WordPress request and uploads JSON output as a 14-day GitHub Actions artifact; GitHub's run/artifact availability is the review notification. Do not place credentials or private editorial material in the config or workflow artifact.

## Providers and policy

`template` is free and local. `openai` is optional and uses your own API billing. `external_json` POSTs source JSON to `editorial.external_json_url`; the endpoint must return the article JSON schema. HTTPS and no redirects are enforced; cross-host endpoints require `allow_external_json_host: true`. Source URLs must come from the supplied briefing. Set `model`, `style`, `language`, `max_output_tokens` (OpenAI output bound), and `source_quality_policy` explicitly. `max_cost_usd` is a policy note only: this version does not estimate or enforce provider dollar spend. Use provider-side billing limits; the scheduled workflow rejects paid/external providers.

## Supported WordPress setups

- **Self-hosted WordPress**: `wordpress.api_base = https://your-domain/wp-json/wp/v2`, `auth_mode = application_password`, set `WP_USERNAME` and `WP_APP_PASSWORD` using environment secrets.
- **WordPress.com via public API proxy**: see `config.wordpress-com.example.json`, `auth_mode = wordpress_com_oauth`, set `WP_CLIENT_ID`, `WP_CLIENT_SECRET`, `WP_USERNAME`, `WP_APP_PASSWORD` securely. The implementation exchanges the app password for an OAuth2 bearer token using the official WordPress.com token endpoint.
- **Existing token**: `auth_mode = bearer`, `WP_BEARER_TOKEN` environment variable.

API routes, auth support and permissions vary by WordPress.com plan/hosting and plugins. WordPress.com sites may require the public API proxy route and bearer-capable permissions; application passwords are not accepted against that proxy. Some hosts/plugins disable REST endpoints, edit context, pagination headers or post creation. Run the synthetic contract tests and verify route/permission behavior with a staging site before use. **No live site has been tested.** See official [WordPress API](https://developer.wordpress.org/rest-api/reference/posts/) and [WordPress.com documentation](https://developer.wordpress.com/docs/api/getting-started/).

## Important safeguards / limitations

- RSS summaries are unverified leads. OpenAI drafts may contain errors. Review all factual claims, citations, image rights and HTML before publication. This starter has **no auto-fact-checker** and **no automatic media upload**.
- The unit tests use synthetic data, not a real WordPress site. Live calls have not been verified.
- Automatic publishing is intentionally **disabled** in the included workflow; use the default draft-first workflow. Do not schedule blind `publish --live`.
- Duplicate prevention is heuristic, checks up to 1000 visible/editable posts, and cannot guarantee semantic uniqueness. It stops if the search is incomplete.
- No credential files, `.env`, production URLs or generated posts should be committed. A GitHub workflow is supplied for tests, not live publishing.

## Community

See `CONTRIBUTING.md`, `docs/ROADMAP.md`, and `SECURITY.md`. Open PRs for tests with mock WordPress APIs, multilingual editorial config, source validation, preview UI, approval gates and optional license-compliant media handling.
