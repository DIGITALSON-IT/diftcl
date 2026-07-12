# Changelog

All notable changes to skill-diftcl are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Changed the public license from MIT to `AGPL-3.0-or-later` and documented
  commercial licensing availability from Digitalson for non-AGPL use cases.

### Documentation

- Added a non-technical legal-practice workflow and copy-ready prompt guide for
  attorney, paralegal, and legal-ops DIFTCL use cases.
- Added a GitHub-rendered Mermaid process map for the legal-practice workflow.

## [1.0.0-rc.4] - 2026-07-02

Public-release hardening: cross-platform (Claude + Codex + Windows) fixes and
environment sanitization ahead of the public launch.

### Changed

- **Skill renamed `skill-diftcl` → `diftcl`.** The invocation is now the brand:
  `$diftcl` in Codex, "use the diftcl skill" in Claude. Install instructions
  clone into a `diftcl` folder; the GitHub repository name is unchanged.
- **CourtListener access is now capability-based, not host-based** across
  `SKILL.md`, `README.md`, `references/courtlistener.md`, and `AGENTS.md`:
  prefer a CourtListener MCP tool when one is in the active tool list (any
  host), else the REST API with `COURTLISTENER_TOKEN`, else mark online checks
  `not_checked`. Removed the incorrect claims that the MCP connector is
  required under Claude and that Codex cannot use a CourtListener MCP.
- **Corrected the Codex install path** to `~/.agents/skills` per the current
  Codex skills documentation, with the legacy `~/.codex/skills` path noted for
  older versions.
- The skill frontmatter description is host-neutral (no longer says "Use when
  Codex needs to…"), and declares `license: MIT`.
- Renamed `references/diftcl-lrh-quote-logic.md` to
  `references/quote-verification-logic.md` and removed internal project
  provenance from its introduction.
- `AGENTS.md` rewritten as a public contributor guide; removed internal
  lab/environment references. `SKILL.md` no longer names specific local
  search/fetch services — it now says to use the host's available web-search
  and URL-fetch tools.
- Codex UI metadata (`agents/openai.yaml`) display name is now
  "DIFTCL — Do It For The Case Law" and the default prompt uses `$diftcl`.

### Fixed

- **Windows: section symbols no longer emit mojibake.** The helpers reconfigure
  stdout/stderr to UTF-8, so `42 U.S.C. § 1983` survives piping to agents and
  files on Windows (previously `�` under the legacy code page). The smoke
  runner decodes subprocess output as UTF-8 to match.
- **Windows: documented launchers that actually exist.** All docs now note that
  `python3` should be `python` or `py` on Windows, and the Claude.ai packaging
  section includes a PowerShell `Compress-Archive` equivalent (with `LICENSE`
  now included in the zip).
- `--json` now wins over mode shortcut flags, so `--authorities --json` emits
  JSON instead of silently printing Markdown.
- README status badge updated (was stuck at rc.1), and all README install
  snippets pin the release tag (`git clone --branch v1.0.0-rc.4 …`).

### Added

- **GitHub Actions CI**: compile check, the 19-case regression smoke suite, and
  the Definition-of-Done commands on a Linux/Windows/macOS matrix (Python 3.9
  and 3.12).
- `CONTRIBUTING.md` and `SECURITY.md`.

## [1.0.0-rc.3] - 2026-07-02

### Documentation

- Added a detailed **"Using DIFTCL in Claude or Codex"** section to the README:
  how to invoke the skill, example prompts for every capability, what happens
  under the hood, and how to enable CourtListener validation. The command-line
  walkthrough is now clearly labeled as the standalone-tool mode.
- Corrected the project positioning: **DIFTCL is an educational AI news service**
  showcasing real-world AI (U.S. federal appellate coverage — not yet state),
  **produced by Digitalson**, the go-to legal technology enablement partner.

## [1.0.0-rc.2] - 2026-06-26

Documentation-only release candidate on top of 1.0.0-rc.1 — no code changes. The
19-case regression smoke suite and skill packaging validation remain green.

### Documentation

- Rewrote `README.md` as a public, open-source-ready document aimed at
  paralegals and lawyers: plain-English capabilities, a prominent "not legal
  advice" disclaimer, a two-modes (AI skill vs. standalone CLI) walkthrough, a
  results-status guide, and confidentiality guidance. Clone URLs point at the
  public GitHub org (`DIGITALSON-IT/skill-diftcl`).
- Corrected the CourtListener access model across `README.md`, `SKILL.md`, and
  `references/courtlistener.md`: the CourtListener **MCP is a Claude connector**
  (the required path for online validation under Claude), while **Codex and the
  standalone CLI have no CourtListener MCP** and use the REST API with
  `COURTLISTENER_TOKEN`.
- Positioned the skill as an open-source tool from **DIFTCL — Do It For The Case
  Law**, an AI-powered court reporting service, with a technology-enablement
  contact at digitalson.com.

## [1.0.0-rc.1] - 2026-06-26

First release candidate. Validated against ~280 real legal documents across two
corpora (federal/GA/FL child-support and civil-rights §1983) with zero genuine
reporter gaps, plus live CourtListener validation/quote checks and skill
packaging validation.

### Fixed

- **Spaced "U. S." Supreme Court citations are now matched.** The federal `U.S.`
  reporter required no internal space, so the common older/typewriter form
  `461 U. S. 352` was missed entirely (found across many real §1983 briefs). The
  pattern now tolerates the space and flags it toward canonical `U.S.`. Verified
  by a recursive audit of 209 civil-rights documents, after which the helper had
  zero genuine reporter gaps.
- **Citations that wrap across a line are now matched.** Reporter abbreviations
  with internal spaces (`Ga. App.`, `F. Supp.`, `S. Ct.`, `L. Ed. 2d`) used a
  literal optional space, so a PDF line break inside the reporter (e.g.
  `114 Ga.\nApp. 630`) broke extraction. Internal separators now tolerate any
  whitespace, and citation `text`/`reporter` fields are whitespace-normalized for
  clean display and table-of-authorities grouping. Verified on a real petition
  where this recovered the one remaining missed citation.
- **PDF reading is robust in batch use.** `read_pdf` previously raised
  `SystemExit` on any failure, which aborted the whole run on a single
  encrypted/corrupt/scanned PDF. It now raises a catchable `ExtractionError` with
  a clear message, the CLI reports it and exits non-zero instead of crashing, and
  a scanned image PDF with no text layer produces a "needs OCR" note rather than a
  silent empty audit.
- **Review packet de-duplicates authorities and doctrines.** A brief that
  mentions "sovereign immunity" eight times now yields one action item
  (`sovereign immunity (8×)`) instead of eight, grouped by doctrine id and by
  normalized authority.
- **State-court citations are now recognized.** `REPORTER_PATTERN` previously
  covered federal and regional reporters but omitted most state official
  reporters, so e.g. Georgia citations (`296 Ga. 793`, `350 Ga. App. 274`) were
  not extracted at all — verified on real Georgia briefs where 16 of 16 case
  citations were missed. Added state/territory reporters with common appellate
  variants (Ga., Ga. App., N.Y., Ill., Mass., Pa., Tex., Fla., Ohio St., and the
  rest), grouped into federal/regional/state lists for maintainability. Federal
  and regional extraction is unchanged; a trailing page number still guards
  against false positives on state abbreviations in prose.
- **Case-name extraction no longer swallows prose lead-ins.** Citations embedded
  in sentences (e.g. "As the Court explained in Brown v. Bd. of Educ., 347 U.S.
  483") now extract the case name as `Brown v. Bd. of Educ.` instead of capturing
  the leading prose. Party names are matched as constrained capitalized tokens,
  `re.IGNORECASE` was removed from the case-citation pattern, and a leading
  signal/lead-in trimmer ("See", "In", "Later in", ...) runs after capture while
  preserving real name openers ("In re", "Ex parte") and names that legitimately
  begin with "The"/"Under"/etc.
- **Table of authorities now groups repeated cites correctly.** A case cited in
  two sentences produces a single TOA entry with the right mention count instead
  of fragmenting into multiple miscounted entries (a consequence of the
  case-name fix).
- **`supra` short-form label no longer over-captures.** "See also Roe, supra, at
  113" yields the label `Roe, supra, at 113` rather than absorbing the preceding
  sentence.
- **Parallel citations parse correctly.** A citation such as
  `347 U.S. 483, 74 S. Ct. 686 (1954)` is captured whole, with its court/year
  parenthetical attached, instead of truncating at the parallel reporter's volume,
  emitting a bogus pincite, and raising a false `missing_parenthetical` error.
- **Missing-comma pincites are detected.** `347 U.S. 483 495` is now flagged with
  `missing_pincite_comma` (previously the second number was silently dropped and
  the check was unreachable).
- Removed a hardcoded personal absolute path from the `AGENTS.md` verification
  steps.

### Added

- **MIT `LICENSE`** (Copyright (c) 2026 DigitalsonIT), replacing the prior
  placeholder license note in the README.
- `python/diftcl_shred.py`: a stdlib-only, cross-platform (Windows/macOS/Linux)
  secure-delete helper for locally written audit artifacts. Dry-runs by default,
  overwrites (random then zero passes) before unlinking, refuses drive roots and
  shallow paths, and supports a `--root` subtree restriction. Documented in the
  README privacy section and covered by a regression smoke case.
- Guidance in `references/courtlistener.md` and `SKILL.md` for CourtListener MCP
  servers that expose only a fuzzy `search` tool (no `citation-lookup` endpoint):
  confirm the exact reporter string in the result's citation list, treat a miss
  as `not_checked` rather than `404`, and fall back to a case-name search.
- Note in `SKILL.md` to collapse whitespace/newlines when normalizing quotes,
  since opinion text frequently wraps a quoted sentence across a line break.
- Regression cases covering prose lead-in case names, parallel citations, TOA
  grouping, missing-comma pincites, `supra` labels, and the business-day calendar
  path (smoke suite grows from 9 to 15 cases).

### Changed

- `README.md` repository layout now lists `CHANGELOG.md`, `CLAUDE.md`,
  `AGENTS.md`, `tests/`, and `python/run_regression_smoke.py`.

[Unreleased]: https://github.com/DIGITALSON-IT/skill-diftcl/compare/v1.0.0-rc.4...HEAD
[1.0.0-rc.4]: https://github.com/DIGITALSON-IT/skill-diftcl/compare/v1.0.0-rc.3...v1.0.0-rc.4
[1.0.0-rc.3]: https://github.com/DIGITALSON-IT/skill-diftcl/compare/v1.0.0-rc.2...v1.0.0-rc.3
[1.0.0-rc.2]: https://github.com/DIGITALSON-IT/skill-diftcl/compare/v1.0.0-rc.1...v1.0.0-rc.2
[1.0.0-rc.1]: https://github.com/DIGITALSON-IT/skill-diftcl/releases/tag/v1.0.0-rc.1
