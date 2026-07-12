# Security Policy

## Reporting a vulnerability

Please report security issues privately via [GitHub Security Advisories](https://github.com/DIGITALSON-IT/skill-diftcl/security/advisories/new) rather than a public issue. We'll acknowledge within a few business days.

## Scope notes

- DIFTCL's Python helpers are stdlib-only and make network requests only when CourtListener validation or user-directed local-rule fetching is explicitly enabled.
- Never include client documents, privileged material, or CourtListener tokens in reports. Reproduce issues with synthetic or public-record text.
- `diftcl_shred.py` is best-effort defense-in-depth, not a forensic guarantee — see the limitations documented in the script and README. Reports that improve its safety checks are welcome.
