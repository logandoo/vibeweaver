# Evidence policy

Evidence under `tests/` is publishable material. It must not contain
plaintext credentials or personal data.

- **No credentials.** Never paste tokens/passwords into logs, screenshots, or
  traces. Redact as `[REDACTED:<kind>:<len>]` (see
  `scripts/state_sanitize.py`).
- **Screenshots.** Crop or mask secrets/PII before saving. A screenshot is a
  document, not an exception.
- **State.** `.vibeweaver/` is gitignored; the audit plugin redacts before
  writing. `python3 scripts/state_sanitize.py --check .vibeweaver/` is the
  named check.
- **Scan.** `python3 scripts/scan_secrets.py --all tests/` must report clean
  before a release. Test fixtures may build fake values at runtime
  (`"AKIA" + "..."`) so the scanner stays meaningful.
- **Leak response.** Rotate the credential FIRST, then open a Class-E record
  for history rewrite (`.gitignore` prevents future commits, not past ones).
- **Retention.** State expires after 14 days and is capped at 5 MB; evidence
  lives with the release it proves.
