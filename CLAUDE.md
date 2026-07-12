# CLAUDE.md - skill-diftcl

This repo defines DIFTCL, a cross-platform agent skill (Claude, Codex, and other SKILL.md hosts) for legal citation extraction, CourtListener validation, and quote verification.

## Constraints

- Do not store copyrighted Bluebook text. Store public links and locally authored citation-audit notes.
- Do not store CourtListener tokens or user legal documents.
- Keep scripts dependency-light and usable in agent containers.
- CourtListener 429 responses are blockers; do not retry aggressively.
- Quote verification must require direct source-text support.
- Attorney/paralegal review output must separate action items, short-form resolution, citation style, and quote support.
- Local-rule population must fetch only user-selected official court/rules sources and must stop on throttling, blocks, or access warnings.
- Deadline calculations must use supplied/configured rule sources and explicit holidays; never infer jurisdiction deadlines from memory.
- Strategy/tactics/contrarian output is issue spotting, not legal advice.
- Doctrine/statute education must separate plain-language orientation from current-law validation.

## Definition of Done

Run the commands below with the platform's Python launcher (`python3` on Linux/macOS; `python` or `py` on Windows).

- `SKILL.md` updated when workflow behavior changes.
- References updated when public API/standards sources change.
- `python3 -m py_compile python/diftcl_citation_audit.py` passes.
- `python3 python/diftcl_citation_audit.py --text "Brown v. Bd. of Educ., 347 U.S. 483, 495 (1954). Id. at 496." --output-format review` passes.
- `python3 python/diftcl_citation_audit.py --list-rule-sources --rule-source-query Minnesota` passes.
- `python3 python/diftcl_citation_audit.py --calendar-from 2026-06-01 --calendar-days 14 --calendar-holidays 2026-06-19` passes.
- `python3 python/diftcl_citation_audit.py --text "Brown v. Bd. of Educ., 347 U.S. 483, 495 (1954)." --strategy` passes.
- `python3 python/diftcl_citation_audit.py --text "42 U.S.C. § 1983 and qualified immunity" --educate` passes.
- `python3 python/run_regression_smoke.py` passes.
- Skill quick validation passes.
