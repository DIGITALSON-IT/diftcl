# AGENTS.md - skill-diftcl

This repository contains DIFTCL (Do It For The Case Law), a legal citation and quote-validation skill for AI coding agents, plus an optional standalone Python helper.

## Scope

- Do not commit API tokens, copied Bluebook text, user legal documents, or privileged legal material.
- Use redacted or synthetic examples in fixtures, issues, and pull requests.
- Treat outputs as legal research support and citation QA, not legal advice.

## Skill Rules

- Keep `SKILL.md` concise and procedural.
- Store only locally authored summaries and public-source links in `references/`.
- Keep deterministic extraction and validation helpers in `python/`.
- Keep matter templates in `templates/` and legal-team workflow detail in `references/`.
- CourtListener access is capability-based: prefer a CourtListener MCP tool when one is in the active tool list; otherwise use the CourtListener REST API with a token from the environment; otherwise mark online checks `not_checked`.
- Preserve DIFTCL quote-validation semantics: citation validity and quote validity are separate checks.
- Local-rule source population must be user-directed. Do not crawl court websites, iterate the registry, or retry blocked requests.
- Deadline calculations must be rule-driven from supplied/configured sources. Do not hardcode jurisdiction deadlines from memory.
- Doctrine/statute education is source orientation and issue spotting, not legal advice or current-law validation.

## Verification

Before pushing changes, run these with your platform's Python launcher (`python3` on most Linux/macOS systems; `python` or `py` on Windows):

```bash
python3 -m py_compile python/diftcl_citation_audit.py
python3 python/diftcl_citation_audit.py --text "Brown v. Bd. of Educ., 347 U.S. 483, 495 (1954)." --json
python3 python/diftcl_citation_audit.py --text "Brown v. Bd. of Educ., 347 U.S. 483, 495 (1954). Id. at 496." --output-format review
python3 python/diftcl_citation_audit.py --list-rule-sources --rule-source-query Minnesota
python3 python/diftcl_citation_audit.py --calendar-from 2026-06-01 --calendar-days 14 --calendar-holidays 2026-06-19
python3 python/diftcl_citation_audit.py --text "Brown v. Bd. of Educ., 347 U.S. 483, 495 (1954)." --strategy
python3 python/diftcl_citation_audit.py --text "42 U.S.C. § 1983 and qualified immunity" --educate
python3 python/run_regression_smoke.py
```

If a skill-validation tool (for example the skill-creator `quick_validate.py`) is available in your environment, run it against the repo root as well.
