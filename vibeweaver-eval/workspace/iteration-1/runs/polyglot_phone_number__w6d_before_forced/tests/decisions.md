# Decisions (AUTO mode)

D-1 | trigger: COV-9 baseline commit not possible (run dir is an untracked subdir of the shared eval repo) | options: (a) commit into shared parent repo, (b) no commit + run-once baseline check + RED evidence | chosen: (b) | why: committing would entangle unrelated sibling runs; baseline recorded via `py_compile` (exit 0) and stub hidden-suite RED (21 failed) | revisit-if: the run dir becomes an isolated git repo.

D-2 | trigger: A4.9 reviewer flagged Important non-ASCII validation gap | options: (a) defer as out-of-spec, (b) add ASCII guard | chosen: (b) | why: closes a real robustness hole at zero cost to the authoritative suite (21/21 still pass) | revisit-if: non-string input support is required.
