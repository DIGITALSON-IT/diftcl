---
name: diftcl
description: "DIFTCL (Do It For The Case Law) legal citation, case-quote, statute/rule, doctrine, local-rule, deadline, and litigation strategy support. Use when extracting case citations, statutes, regulations, rules, constitutional provisions, or doctrines from text, PDFs, DOCX, HTML, or pasted legal prose; checking U.S. case citations against Bluebook-style court-document norms; validating citations through CourtListener (MCP or public REST API); verifying quoted language against cited case text; calculating rule-driven litigation deadlines from user-supplied jurisdiction rules; producing plain-language doctrine/statute education notes; or producing strategy, tactics, and contrarian issue-spotting outputs."
license: "AGPL-3.0-or-later"
---

# DIFTCL Legal Citation

Use this skill to audit U.S. legal citations and case quotes. Treat it as a legal research and quality-control workflow, not legal advice.

## Quick Workflow

1. Identify the input:
   - Pasted prose, local text/Markdown/HTML/PDF/DOCX file, URL, or a single cite.
   - Ask only if the user has not provided enough input to locate the document or citation.
2. Extract text. Prefer `python/diftcl_citation_audit.py` for local files and pasted text when a local helper is useful.
3. Extract citations and quoted strings.
4. Validate in layers:
   - Bluebook-style structure and likely citation-form problems.
   - CourtListener citation lookup for case existence, canonical reporter normalization, ambiguity, and cluster metadata.
   - Quote verification against user-supplied source text first, then CourtListener opinion text when available.
   - Statute, rule, regulation, constitutional provision, and doctrine extraction when requested.
5. For attorney/paralegal workflows, read `references/attorney-paralegal-workflows.md` and use a matter-level `diftcl.yaml` when repeat audits or filing-court settings matter.
6. For local-rule-sensitive work, read `references/local-rule-sources.md`. Fetch only user-selected court/rules sources; never crawl court websites or iterate over the whole registry.
7. For deadlines, read `references/litigation-calendar-strategy.md`. Use configured rules/orders only; do not calculate jurisdiction deadlines from memory.
8. For doctrine/statute education, read `references/doctrine-statute-education.md`. Explain as research support, cite official source hints, and avoid legal advice.
9. For strategy, tactics, or contrarian review, read `references/litigation-calendar-strategy.md` and ground output in extracted citations, quote status, statute/rule/doctrine extraction, local-rule status, calendar configuration, and user facts.
10. Report findings as:
   - `ok` for valid and supported.
   - `warning` for style issues or unresolved ambiguity.
   - `error` for missing/invalid citation or quote not found in source.
   - `not_checked` when authority text or CourtListener access is unavailable.

## Tools

Run the optional Python helper. It needs Python 3.9+ (stdlib only). Invoke it with whichever launcher the host provides: `python3` on most Linux/macOS systems, `python` or `py` on Windows.

```bash
python3 python/diftcl_citation_audit.py --input path/to/document.md
python3 python/diftcl_citation_audit.py --text "Brown v. Bd. of Educ., 347 U.S. 483, 495 (1954)"
python3 python/diftcl_citation_audit.py --input brief.docx --courtlistener --verify-quotes
python3 python/diftcl_citation_audit.py --cite "576 US 644" --courtlistener --json
python3 python/diftcl_citation_audit.py --input brief.pdf --config diftcl.yaml --output-format review
python3 python/diftcl_citation_audit.py --input brief.docx --toa
python3 python/diftcl_citation_audit.py --list-rule-sources --rule-source-query "Minnesota"
python3 python/diftcl_citation_audit.py --calendar-from 2026-06-01 --calendar-rules-file calendar-rules.json --calendar-rule response-after-service
python3 python/diftcl_citation_audit.py --input brief.md --strategy --strategy-position defense
python3 python/diftcl_citation_audit.py --input brief.md --authorities
python3 python/diftcl_citation_audit.py --text "42 U.S.C. § 1983 and qualified immunity" --educate
python3 python/run_regression_smoke.py
```

Choose the CourtListener access path by capability, not by host. Check in this order:

1. **A CourtListener MCP tool is in the active tool list** (any host — e.g. the CourtListener connector in Claude, or a user-configured MCP server in Codex): prefer it for lookup/fetch and use the script for local extraction/style checks.
2. **No MCP, but network access and a `COURTLISTENER_TOKEN` (or anonymous quota) are available:** use the public REST API documented in `references/courtlistener.md`.
3. **No CourtListener access at all:** run local extraction, citation-form, TOA, deadline, and source-text quote checks only, and mark anything online-dependent as `not_checked`.

Use the host's available web-search and URL-fetch tools for fresh public-reference checks when standards or API behavior may have changed:

```text
Search: Bluebook case citation Rule 10 public guide court year parenthetical pincite
Fetch: CourtListener citation lookup API and case law API docs
```

Do not store copied Bluebook text in the skill. Store only locally authored summaries, public-source links, and short examples.

## Local Rules

Read `references/local-rule-sources.md` when the user identifies a filing court, asks for local-rule population, or wants court-specific citation requirements. Source seeds live in `references/court-rule-source-registry.json`.

Mandatory safety rules:

- Require a user-selected `local_rules_url`, `local_rules_court_id`, or specific filing court before fetching local rules.
- Do not crawl, spider, or enumerate court websites.
- Do not fetch all state or federal sources to populate rules.
- Do not use PACER, CM/ECF, login-protected systems, POST forms, or docket-search endpoints.
- Stop on `429`, `403`, captcha, robots/access warnings, or other block signals.
- Default to zero retries and no more than three requests for one user-selected court-rule population task.
- Cache and cite rule sources by URL and retrieval date when possible.

## Citation Audit Rules

Read `references/bluebook-case-citation.md` before making a detailed citation-style call. The skill focuses on court-document case citations:

- Full case citation should generally have case name, volume, reporter, first page, optional pincite, and court/year parenthetical.
- Use canonical reporter abbreviations where known, especially `U.S.`, `S. Ct.`, `L. Ed. 2d`, `F.`, `F.2d`, `F.3d`, `F.4th`, `F. Supp.`, `F. Supp. 2d`, and `F. Supp. 3d`.
- Use a comma before ordinary page pincites: `123 F.3d 456, 460`.
- Use `at *N` for Westlaw/Lexis star-page pincites.
- Include court and year in the parenthetical for federal appellate/district cases and most state cases; Supreme Court citations to `U.S.` usually need only the year.
- Preserve local court rules and jurisdiction-specific citation requirements over generic Bluebook-style defaults when the user identifies a filing court.
- Treat `Id.`, `supra`, and abbreviated short forms as separate resolution tasks. Do not mark them validated merely because a nearby full citation is valid.

## Deadlines And Strategy

Read `references/litigation-calendar-strategy.md` for deadline and strategy workflows.

Deadline rules:

- Use `templates/calendar-rules.json` as a starting point for matter-specific deadline rules.
- Do not hardcode or invent filing deadlines. Require a controlling rule, order, statute, or user-selected official source.
- Always report trigger date, rule ID/source, counting method, holidays used, weekend/holiday roll rule, and attorney-review warning.
- Mark ad hoc calculations as `not_authoritative`.

Strategy/tactics/contrarian rules:

- Keep outputs as issue spotting and preparation support, not legal advice.
- Separate strategy, tactics, and contrarian review.
- Ground each recommendation in extracted citations, quote status, local-rule status, deadline status, or explicit assumptions.
- Treat missing facts, missing rule sources, unchecked quotes, and unresolved short forms as action items.

## Doctrine And Statute Education

Read `references/doctrine-statute-education.md` when extracting statutes, regulations, procedural rules, constitutional provisions, legal doctrines, standards, elements, defenses, or plain-language educational notes.

Rules:

- Keep statutes/rules/regulations separate from case citations.
- Do not use CourtListener citation lookup to validate statutes or rules.
- Prefer official sources: OLRC U.S. Code, eCFR, Congress.gov, GovInfo, state legislature/code sites, and official court rules.
- Use Cornell LII Wex only for educational orientation unless controlling authority is separately verified.
- Flag incomplete statute references and doctrine labels that need element-by-element analysis.
- Do not assume a statute is current, effective, or controlling without source verification.

## Quote Validation

Read `references/quote-verification-logic.md` before quote audits. The default quote rule is strict:

- Never accept an LLM-generated quote because the citation exists.
- A quote is supported only if its normalized text appears in the cited authority text or in a user-provided source excerpt.
- Normalize before comparing: lower-case, strip punctuation, and collapse all whitespace (including newlines) to single spaces. Opinion text often wraps a quoted sentence across a line break, so a raw substring match produces false negatives.
- Preserve author/case metadata separately from quote validity.
- Flag paraphrases presented in quotation marks as errors unless exact source text is found.
- For short quotes under 24 normalized characters, report low confidence unless the source match is exact and context is clear.

## CourtListener Behavior

Read `references/courtlistener.md` when using CourtListener. Important constraints:

- Online case validation and opinion-text quote checks require CourtListener access: a **CourtListener MCP tool** when one is in the active tool list, otherwise the **REST API with `COURTLISTENER_TOKEN`**. Without either, these checks are `not_checked`.
- Citation lookup validates case reporter citations, not statutes, `id.`, `supra`, law journals, or incomplete citations without volume/page.
- Status `200` means found; `300` means ambiguous; `400` means malformed/unknown reporter; `404` means valid-looking but not found; `429` means throttled.
- These status codes apply to the `citation-lookup` endpoint. If the available MCP exposes only a fuzzy `search` tool (no `citation-lookup`), those codes do not apply: confirm the exact reporter string appears in the result's citation list, treat a miss as `not_checked` rather than `404`, and fall back to a case-name search. See `references/courtlistener.md`.
- Clusters contain case-level metadata and parallel citations. Opinions contain text; prefer `html_with_citations` when fetching opinion text through the API.
- Respect throttles. Batch documents and stop on 429 instead of retrying aggressively.

## Output

Give the user a concise table or bullet list with:

- Extracted citation text and location.
- Page/line location when the helper can provide it.
- Canonical/normalized citation when available.
- CourtListener status and matched case name when available.
- Bluebook-style issues and suggested correction.
- Quote status for each quoted string tied to a citation.
- Short-form references requiring manual mapping.
- Table-of-authorities draft entries when requested.
- Deadline calculations and rule-source warnings when requested.
- Strategy/tactics/contrarian issue-spotting output when requested.
- Extracted statutes, regulations, rules, constitutional provisions, doctrines, and education notes when requested.
- Any limits, such as missing CourtListener token, unavailable source text, or ambiguous cluster matches.

When a citation or quote is wrong, state the reason concretely and provide the corrected form only when the available sources support it.

For review-packet output, prioritize action items for legal teams: invalid citations, ambiguous authorities, unsupported quotes, unchecked quotes, missing pincites near quotes, and unresolved short forms.
