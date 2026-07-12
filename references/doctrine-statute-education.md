# Doctrine, Statute, And Rule Education

Use this reference when the user asks DIFTCL to extract statutes, regulations, procedural rules, constitutional provisions, doctrines, elements, standards, or educational explanations.

## Source Priority

Prefer official or public legal sources:

- U.S. Code, Office of the Law Revision Counsel: https://uscode.house.gov/
- eCFR, official electronic Code of Federal Regulations: https://www.ecfr.gov/
- Congress.gov legislation text and status: https://www.congress.gov/
- GovInfo: https://www.govinfo.gov/
- State legislature or state code official websites selected by the user.
- Court rules from official court websites selected under `references/local-rule-sources.md`.
- Cornell LII Wex for plain-language legal doctrine orientation: https://www.law.cornell.edu/wex/index.html

Use non-official education sources only as orientation. Do not treat them as controlling law.

## Extraction Targets

Extract and label:

- U.S. Code citations, such as `42 U.S.C. § 1983`;
- Code of Federal Regulations citations, such as `29 C.F.R. § 825.220`;
- federal procedural/evidence/appellate/bankruptcy rules, such as `Fed. R. Civ. P. 12(b)(6)`;
- state statutes, such as `Minn. Stat. § 181.13`;
- constitutional provisions, such as `U.S. Const. amend. XIV`;
- named legal doctrines, standards, and defenses.

Keep statutes/rules separate from case citations. CourtListener citation lookup does not validate statutes or procedural rules.

## Education Output

For each extracted authority or doctrine, provide:

- exact text found;
- type;
- location;
- normalized citation when safe;
- official source path or source hint;
- what the user needs to verify;
- plain-language educational note when known;
- whether the item is controlling, persuasive, background, or unknown based only on user-provided facts.

Do not provide a definitive legal conclusion unless the user supplies the controlling source and relevant facts. Use phrases such as "research note," "verify," and "issue to check" rather than "this wins" or "this applies."

## Doctrine Review

Doctrine extraction should identify legal concepts that may require element-by-element analysis. Examples include:

- standing;
- mootness;
- ripeness;
- res judicata / claim preclusion;
- collateral estoppel / issue preclusion;
- qualified immunity;
- sovereign immunity;
- strict scrutiny;
- rational basis;
- burden shifting;
- exhaustion;
- waiver;
- preservation;
- statute of limitations;
- laches;
- irreparable harm;
- likelihood of success on the merits;
- standard of review.

For doctrine education, separate:

- doctrine name;
- likely procedural posture;
- elements or questions to research;
- cited statutes/cases tied to it;
- missing facts;
- adverse/contrarian angle.

## Safety

- Do not validate a statute from a case citation tool.
- Do not assume a statute is current without checking the official source.
- Do not infer effective dates, amendments, savings clauses, exhaustion requirements, or limitations periods from memory.
- Do not turn educational summaries into legal advice.
- When the document cites a statute without a section, flag it as incomplete.
