# Compatibility matrix (w18.3)

Only combinations with a CI leg are **supported**. Everything else is either an
**adapter** (runs, but no equal-semantics promise) or **unsupported**.

| Host | Node | Python | OS | Status | Evidence |
|---|---|---|---|---|---|
| opencode v1 | 20 | 3.9 | Linux | supported | `verify.yml` ubuntu 3.9 |
| opencode v1 | 20 | 3.12 | Linux | supported | `verify.yml` ubuntu 3.12 |
| opencode v1 | 20 | 3.9 | macOS | supported | `verify.yml` macos 3.9 |
| opencode v1 | 20 | 3.12 | macOS | supported | `verify.yml` macos 3.12 |
| opencode v1 | 20 | 3.9 | Windows | supported (POSIX trust fixtures skipped) | `verify.yml` windows 3.9 |
| opencode v1 | 20 | 3.12 | Windows | supported (POSIX trust fixtures skipped) | `verify.yml` windows 3.12 |
| opencode v2 | 20 | 3.9 / 3.12 | Linux/macOS/Windows | supported | same matrix; v2 loader unit tests |
| opencode v1/v2 | 22 | any | any | adapter | no Node 22 CI leg yet |
| Claude Code / Codex / Gemini | any | any | any | adapter | no equal-semantics claim (D-002) |
| Chatbot / hosted service | any | any | any | unsupported | out of scope (D-005) |

## Model class

`VIBEWEAVER_MODEL_CLASS=strong|weak|local` is explicit. Unknown/unset defaults to
**core + warning**, never a guess. The full profile is an explicit opt-in.

## Known gaps

- Windows skips the POSIX shell trust fixtures (`gate_trust/*.sh`); the Python
  and Node suites still run there.
- Hosts without a `tool.execute.before` hook degrade the destructive/risk gate
  to post-hoc `GATE-WARNING` (adapter-only, no pre-execution stop).
- `vibeweaver-mini` has its own installers and its own platform counts; those
  are reported per platform, not as one universal number.
