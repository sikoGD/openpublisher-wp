# Checklist for the first public release

- [ ] Independently review all source files, license, names, and setup text.
- [ ] Confirm no production `config.json`, `.env`, site ID, URL, username, client credentials, app password or unpublished article was copied.
- [ ] Validate with synthetic tests and mock WordPress endpoints before any live testing.
- [ ] Keep default dry-run and manual fact-check/approval gates.
- [ ] Publish this directory into a **new public repository**, never change visibility of the original extrasouls-publisher.
- [ ] Create an example-based setup guide, Issues and contributor documentation.
- [ ] Verify credentials with a throwaway WordPress test site, not a production site.
