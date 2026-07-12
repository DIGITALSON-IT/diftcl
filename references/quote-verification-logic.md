# DIFTCL Quote Verification Logic

The DIFTCL quote guard: a citation being real never makes its quote real. The two are verified independently.

## Rule

A quoted case statement is valid only when the quoted text can be found in the cited authority source text after conservative normalization. Case identity, author identity, and quote validity are separate facts.

## Normalization

Use this for searching only:

1. lower-case;
2. strip punctuation;
3. collapse whitespace;
4. require a meaningful quote length, default 24 normalized characters;
5. compare the normalized quote against normalized authority text.

Do not rewrite the displayed quote to the normalized form. Keep the user's original quote text, but label it unsupported if it does not match.

## Workflow

1. Extract quoted strings near each citation. Use a local window around the citation when the user has not explicitly paired quotes and cites.
2. Resolve the citation through CourtListener.
3. Fetch candidate opinion text from matched clusters when possible.
4. Check the quote against:
   - user-supplied source text for that case;
   - CourtListener opinion text;
   - any official opinion PDF/text the user provided.
5. Return `verified` only for direct text matches.

## Findings

- `verified`: quote text found in authority source.
- `not_found`: quote text is not present in available authority text.
- `too_short`: quote is too short for reliable normalized matching.
- `ambiguous_authority`: citation resolves to multiple CourtListener clusters and quote was not tied to a selected cluster.
- `not_checked`: no authority text was available.

## Guardrail

Do not infer quote validity from a summary, syllabus, headnote, case title, or the fact that a citation exists. When the source text is unavailable, say the quote was not checked.
