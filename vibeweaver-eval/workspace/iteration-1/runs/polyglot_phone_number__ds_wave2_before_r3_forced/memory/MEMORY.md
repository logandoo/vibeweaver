# MEMORY.md — phone_number exercise

Project: canonical Exercism "Phone Number" (NANP cleaning) exercise — single-file
Python task in `phone_number.py`. No service, no UI, no `script/`, no config.toml.

## Topics

- [✅ fix_phone_number](fix_phone_number.md) — solution shape + validated approach

## Notes

- Verification is logic-only: executed Python runs with on-disk log
  (`tests/red_green.log`) — direct-read verifier, no Playwright/mm-probe
  (no browser output).
- Interface: `PhoneNumber(number).number`, `.area_code()`, `.pretty_print()`.
