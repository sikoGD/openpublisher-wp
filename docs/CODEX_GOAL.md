# Codex goal � generalized self-hosted/WordPress.com publishing platform

Use `sikoGD/extrasouls-publisher` as **private design reference only**, never change or publish that repository, production website credentials or private editorial data. Work only in this new public starter.

1. Keep config independent of any one site; support custom WordPress REST URL, managed WordPress.com OAuth and independently owned RSS sources.
2. Verify authenticated flows against mocked WordPress.org and WordPress.com APIs, including timeouts, redirects, expired tokens, permissions, and pagination. Never log secrets.
3. Add an editorial preview/approval queue and site-specific configuration validation. All generated content should remain a draft until a human has fact-checked and approved it.
4. Introduce a provider interface for OpenAI and optional third-party or external JSON generation without requiring paid providers. Make model, style, source quality policy and price controls explicit.
5. Add more robust semantic duplicate detection without making unsubstantiated uniqueness claims.
6. Create a scheduled GitHub Actions pipeline only for safe draft generation and review notification. Do not schedule unreviewed live publishing.
7. Document setup on self-hosted WordPress, WordPress.com public API proxy and common incompatibilities. Build synthetic integration tests.
8. Commit with passing tests and changelogs after each milestone, keeping the original ExtraSouls instance independent and unchanged.

Deliver a clean release candidate suitable for community contribution, not an insecure shared multi-tenant SaaS.
