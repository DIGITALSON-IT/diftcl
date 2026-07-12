# Contributing to DIFTCL

Thanks for helping make citation auditing better. Bug reports, citation-format edge cases, new state-reporter coverage, and documentation improvements are especially welcome.

## Ground rules

- **Never include real client documents, privileged material, or client-identifying details** in issues, pull requests, or test fixtures. Use redacted or synthetic examples.
- **Do not contribute copyrighted Bluebook text.** References must be locally authored summaries with links to public sources.
- Keep the Python helpers **stdlib-only** (Python 3.9+) so they run in agent containers with no installs.
- The skill's behavior lives in `SKILL.md` and `references/`; the standalone tool lives in `python/`; matter templates live in `templates/`.

## Before you open a PR

Run the verification suite with your platform's Python launcher (`python3` on Linux/macOS; `python` or `py` on Windows):

```bash
python3 -m py_compile python/diftcl_citation_audit.py
python3 python/run_regression_smoke.py
```

CI runs the same checks on Linux, Windows, and macOS.

If your change alters workflow behavior, update `SKILL.md`. If it alters extraction or validation behavior, add a regression case to `tests/fixtures/regression_cases.json`. Record notable changes in `CHANGELOG.md` under `[Unreleased]`.

## Reporting citation bugs

The most useful bug report is a minimal text snippet (synthetic or from a public opinion) plus what DIFTCL extracted versus what it should have extracted.
