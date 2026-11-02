# Codex goal: complete Open Publisher for WordPress OSS import

This is a clean public version of a private ExtraSouls publishing automation. NEVER copy private site identifiers, tokens, application passwords, sensitive configuration, or the original repository's private history.

1. Import `openpublisher-wordpress-oss-starter.zip` into the root of this repository, without its parent folder. Reconcile the MIT license and .gitignore, replacing the placeholder README.
2. Run `python -m unittest discover -s tests -v`. Tests must work with synthetic data and without network credentials.
3. Support configurable feeds, editorial categories and site identity instead of hardcoded ExtraSouls settings.
4. Support WordPress REST API and, separately, WordPress.com using each documented authentication flow; test against mocks first.
5. Require human review by default. Publication, automated schedules and image uploads must be explicit opt-ins.
6. Add idempotency and topic deduplication, publish-state tracking, safe handling of untrusted feed data and credentials, retries with bounds, and rate limits.
7. Create a GitHub Actions workflow with minimal permissions and local CLI support; never print secrets.
8. Update README, CONTRIBUTING, SECURITY, example configurations and CI.
9. Commit and push at each validated milestone. Do not change private extrasouls-publisher or publish to ExtraSouls during tests.

Success: newcomers can independently install/configure, preview drafts, and safely publish to their own WordPress after explicit approval.