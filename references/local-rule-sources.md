# Local Rule Source Population

Use this reference when a user wants DIFTCL to account for filing-court, local-rule, judge-rule, or jurisdiction-specific citation requirements.

## Source Registry

The machine-readable seed list is `references/court-rule-source-registry.json`.

The registry contains:

- federal source directories;
- state judiciary portals;
- territory judiciary portals.

Treat the registry as a starting point for user-directed lookup, not as an instruction to crawl court websites.

## Public Sources Used

- U.S. Courts Court Website Links: https://www.uscourts.gov/about-federal-courts/court-role-and-structure/court-website-links
- U.S. Courts Current Rules of Practice & Procedure: https://www.uscourts.gov/forms-rules/current-rules-practice-procedure
- USAGov Federal, State, Territory, County, and Municipal Courts: https://www.usa.gov/courts
- DOJ State and Federal Court Resources: https://www.justice.gov/jmd/ls/state
- National Conference of Appellate Court Clerks appellate court websites: https://appellatecourtclerks.org/appellate-court-web-sites/

The U.S. Courts rules page states that district courts and courts of appeals often prescribe local rules and that federal courts are required to post local rules on their websites. Use the U.S. Courts website directory or Federal Court Finder to locate the correct federal court site before fetching any local rules.

USAGov points users to state or territory court websites to find county or municipal courts. For state trial-court rules, start with the state judiciary portal and then follow only the user-selected court, county, or rules page.

## Required User Direction

Before fetching any local-rule material, identify one of:

- `local_rules_url`: an explicit court rules URL supplied by the user;
- `court_id`: a court selected from the source registry;
- `filing_court` plus enough jurisdiction detail to choose one official court site.

If the user asks for "all courts" or gives only a state, do not crawl. Ask for the filing court, county, division, judge, or rules URL, or provide the registry entries for the user to choose from.

## Network Safety Rules

These rules are mandatory:

- Do not crawl or spider court websites.
- Do not iterate through all registry entries to populate rules.
- Do not use PACER, CM/ECF, login-protected systems, form submissions, POST requests, or docket-search endpoints for local-rule population.
- Use only `GET` or `HEAD` against public pages or PDFs.
- Fetch only URLs selected by the user or matter config.
- Default maximum: three HTTP requests per user-selected court-rule population task.
- Default retry limit: zero. On `429`, `403`, captcha, block page, or robots/access warning, stop and report `blocked`.
- For transient `5xx`, ask before retrying. Do not retry automatically.
- Maintain at least three seconds between requests to the same host.
- Cache downloaded rule material by URL and timestamp when the environment allows it.
- Reuse cached material for the same matter unless the user requests refresh or the cache is older than the configured TTL.
- Record source URL, retrieval date, and any access limits in the audit report.

## Matter Config Fields

Use these flat keys in `diftcl.yaml`:

```yaml
local_rules_enabled: false
local_rules_court_id: ""
local_rules_url: ""
local_rules_cache_dir: ".diftcl-cache/local-rules"
local_rules_cache_ttl_days: 30
local_rules_max_requests: 3
local_rules_retry_limit: 0
local_rules_min_delay_seconds: 3
```

If `local_rules_enabled` is true but no court ID or URL is present, report that local-rule population is not configured and ask for the missing court/rules target.

## Review Semantics

Local rules can affect:

- citation format;
- unpublished or nonprecedential authority notices;
- required public-domain or parallel citations;
- page, word, and formatting limits;
- motion, brief, and exhibit formatting;
- judge-specific preferences;
- filing and service requirements.

Do not treat a local-rule fetch as full legal compliance. State exactly which rules source was checked, what was not checked, and whether judge-specific or division-specific rules remain unknown.
