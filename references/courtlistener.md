# CourtListener Validation Notes

Use CourtListener for authority existence, normalized reporter citations, ambiguity detection, case metadata, and quote source text.

## Sources Checked

- Citation Lookup and Verification API: https://www.courtlistener.com/help/api/rest/v4/citation-lookup/
- Case Law APIs: https://wiki.free.law/c/courtlistener/help/api/rest/v4/case-law
- CourtListener: https://www.courtlistener.com/

## Citation Lookup

Endpoint:

```text
POST https://www.courtlistener.com/api/rest/v4/citation-lookup/
```

Form modes:

```text
text=<blob containing citations>
volume=<volume>&reporter=<reporter>&page=<page>
```

Use `Authorization: Token $COURTLISTENER_TOKEN` when a token is available or required.

Returned status meanings:

| Status | Meaning | Audit Result |
| --- | --- | --- |
| 200 | Citation parsed and matched a CourtListener cluster | Valid authority match |
| 300 | Citation parsed but matched multiple clusters | Ambiguous; user or context must choose |
| 400 | Looks like a citation but reporter is unknown/invalid | Citation-form error |
| 404 | Valid-looking citation but not found | Authority not verified |
| 429 | Request exceeded API limits | Stop or batch; do not retry aggressively |

Important limits from the public docs:

- Text lookup accepts blocks up to 64,000 characters.
- A request looks up at most 250 citations.
- The API does not look up statutes, law journals, `id.`, `supra`, or incomplete citations without volume and page.

## Case-Law Objects

The main hierarchy is:

```text
court -> docket -> cluster -> opinion
```

Use cluster metadata for case names and parallel citations. Use opinion objects for text. When fetching opinion text, prefer `html_with_citations` over `plain_text` if present; strip markup before quote matching.

CourtListener opinion URLs usually contain cluster IDs, not opinion IDs. For a URL like:

```text
https://www.courtlistener.com/opinion/2812209/obergefell-v-hodges/
```

Fetch the cluster:

```text
https://www.courtlistener.com/api/rest/v4/clusters/2812209/
```

Then follow `sub_opinions` to fetch opinion text.

## Access Order (MCP vs REST)

Choose the access path by capability, in this order:

1. **CourtListener MCP tool in the active tool list** — any host. Claude offers a
   CourtListener connector in its directory; other hosts (Codex, standalone CLIs)
   can configure a CourtListener MCP server themselves.
2. **REST API** with `Authorization: Token $COURTLISTENER_TOKEN` (below) when
   network access is available and no MCP tool is present.
3. **No access** — mark online-dependent checks `not_checked`.

When an MCP tool is in the active tool list, prefer it over raw HTTP and
preserve the same validation semantics:

1. citation lookup or search;
2. cluster disambiguation;
3. opinion-text fetch;
4. normalized quote search.

If no CourtListener access is available on any host, run local extraction, style, TOA,
deadline, and source-text quote checks only, and mark online-dependent results
`not_checked`.

## Search-Only MCP Servers (No Citation-Lookup Endpoint)

Not every CourtListener MCP exposes the `citation-lookup` endpoint above. Many
expose only a fuzzy `search` tool plus generic endpoint calls. The clean
`200/300/400/404` status semantics do **not** apply to those servers, and a fuzzy
citation search is unreliable for exact validation. When you only have search:

- Search by the citation, but treat a match as valid **only if the exact reporter
  string you are checking appears verbatim in the result's parallel-citation
  list** (e.g. require `163 U.S. 537` to be one of the returned citations). Fuzzy
  search tokenizes loosely and returns cross-reporter noise such as
  `163 L. Ed. 2d 537` for a query of `163 U.S. 537`.
- Treat a no-result or no-exact-match as **inconclusive (`not_checked`), not a
  definitive `404`**. The citation may be real but unindexed by that search path.
- On a miss, fall back to a **case-name search** and confirm the reporter string
  in the returned citations before reporting the authority as found. (Example:
  a citation search for `163 U.S. 537` can miss *Plessy v. Ferguson* even though a
  case-name search returns it with the exact `163 U.S. 537` citation.)
- For quote verification, fetch opinion text by cluster/opinion ID and try the
  text fields in order (`plain_text`, then `html_with_citations`, then
  `html_lawbox`); some opinions populate only one. Strip markup and collapse
  whitespace before matching (see `quote-verification-logic.md`).
