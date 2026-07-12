<div align="center">

# ⚖️ DIFTCL — Do It For The Case Law

### A citation-audit and litigation-support assistant for lawyers, paralegals, and legal-ops teams.

*Pull every citation out of a brief, confirm the cases are real, catch made-up quotes, draft a table of authorities, calculate deadlines, and spot weaknesses — before the document goes out the door.*

[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL--3.0--or--later-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Status: Release Candidate](https://img.shields.io/badge/Status-v1.0.0--rc.4-orange.svg)](CHANGELOG.md)
[![Works with Claude & Codex](https://img.shields.io/badge/Works%20with-Claude%20%26%20Codex-7C3AED.svg)](#two-ways-to-use-it)
[![Not legal advice](https://img.shields.io/badge/⚠️-Not%20legal%20advice-critical.svg)](#important-not-legal-advice)

</div>

---

> ⚠️ **Important — this is _not_ legal advice.** DIFTCL is a **quality-control and research-support tool**. It helps you find problems faster; it does **not** make legal judgments, and it does **not** replace a licensed attorney's review. Nothing it produces should be filed, served, or relied upon without independent human verification. See the [full disclaimer](#important-not-legal-advice).

---

## Table of Contents

- [What is DIFTCL?](#what-is-diftcl)
- [Why it exists](#why-it-exists)
- [What it can do](#what-it-can-do)
- [Two ways to use it](#two-ways-to-use-it)
- [Installation](#installation)
- [Using DIFTCL in Claude or Codex](#using-diftcl-in-claude-or-codex)
- [Using the command-line tool](#using-the-command-line-tool)
- [Common tasks, step by step](#common-tasks-step-by-step)
- [Understanding the results](#understanding-the-results)
- [CourtListener validation](#courtlistener-validation)
- [Confidentiality & data handling](#confidentiality--data-handling)
- [⚠️ Important: Not Legal Advice](#important-not-legal-advice)
- [Current limitations](#current-limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [About](#about)

---

## What is DIFTCL?

**DIFTCL ("Do It For The Case Law")** reads a legal document — a brief, motion, memo, or order in Word, PDF, HTML, or plain text — and audits the law inside it. In one pass it can:

- **find every case citation** and tell you exactly where it appears (page and line);
- **flag citation-form problems** (the kind a cite-checker hunts for);
- **confirm each case actually exists** using [CourtListener](https://www.courtlistener.com/), the free public case-law database;
- **check that quotations are real** — that the quoted words genuinely appear in the cited opinion;
- **pull out statutes, rules, regulations, constitutional provisions, and doctrines** with links to official sources;
- **draft a Table of Authorities**;
- **calculate filing deadlines** from the rules *you* give it;
- **surface strategic issues** for attorney review.

It works two ways: as an **AI assistant skill** (you simply ask Claude or Codex to "audit the citations in this brief"), or as a **standalone command-line tool** you run on your own machine. Either way, **a human stays in the loop** — DIFTCL is built to make review faster and more consistent, not to replace professional judgment.

> **DIFTCL — Do It For The Case Law** is an **educational AI news service** ([doitforthecaselaw.com](https://doitforthecaselaw.com)) that showcases what AI can do in the real world — with neutral, accessible coverage of U.S. federal appellate court decisions. This skill is one of the **open-source tools** we share with the legal community. Produced by **Digitalson**, your go-to legal technology enablement partner. See [About](#about).

---

## Why it exists

Cite-checking is slow, repetitive, and unforgiving. A single fabricated case, a quotation that doesn't actually appear in the opinion, a missing pincite, or a blown deadline can sink a filing — and these mistakes are easy to miss when you're reviewing forty pages by hand. The risk has only grown now that AI-drafted briefs can contain **confident-sounding citations and quotes that simply do not exist.**

DIFTCL automates the mechanical first pass so attorneys and paralegals can spend their time on judgment, not on hunting commas and chasing reporters. It is deliberately conservative: it separates "this case exists" from "this quote is real" from "this citation is formatted correctly," and it never pretends to certainty it doesn't have.

---

## What it can do

| Capability | In plain English |
|---|---|
| **Citation extraction** | Finds U.S. **federal and state** case citations in your document — including Supreme Court, federal circuits/districts, and state reporters (e.g. `347 U.S. 483`, `296 Ga. 793`, `433 So. 2d 1282`) — with the page and line of each. Handles text copied out of PDFs, even when a citation wraps across a line. |
| **Citation-form review** | Flags common Bluebook-style problems: `vs.` instead of `v.`, non-standard reporters like `US` or `F3d`, a missing comma before a pincite, a missing court/year parenthetical, and more. |
| **Case validation** | Confirms a cited case actually exists via CourtListener, and surfaces the canonical name, court, and date. Catches fabricated or mis-cited authorities. |
| **Quote verification** | Checks whether quoted language actually appears in the cited opinion (or in source text you provide). Designed to catch **the "hallucinated quote" problem** head-on. It treats "the case is real" and "the quote is real" as two separate questions. |
| **Short-form flagging** | Identifies `Id.` and `supra` references that a human needs to map back to a full citation. |
| **Table of Authorities** | Drafts a TOA: each authority, its citation, how many times it appears, and where. |
| **Statutes, rules & doctrines** | Extracts U.S. Code, C.F.R., Federal Rules, state statutes, constitutional provisions, and named doctrines (standing, qualified immunity, exhaustion, etc.) — kept **separate** from case law, with pointers to official sources to verify. |
| **Plain-language education** | Produces short, neutral "research note" explanations of extracted doctrines and authorities — what to check and where, never a legal conclusion. |
| **Deadline calculator** | Calculates litigation deadlines from **rules you supply** (a scheduling order, a local rule, a statute). Reports the trigger date, counting method, holidays used, and weekend/holiday roll — and always tells you to confirm it. It will **never** invent a jurisdiction's deadline from memory. |
| **Strategy & contrarian review** | Issue-spotting for attorney review: strongest/weakest authorities, unsupported quotes, missing pincites, and the angles opposing counsel might attack. |
| **Review packets** | Bundles everything into an attorney/paralegal action list, prioritized by what matters most (invalid cites, unsupported quotes, unresolved short forms). |
| **Local-rule directory** | Ships a registry of official federal/state/territory court websites so you can look up the right local rules — without crawling or scraping anything. |

---

## Two ways to use it

### 1. As an AI assistant skill (recommended for most users)

Install DIFTCL as a **skill** for [Claude](https://claude.com) (Claude Code, Claude.ai, or the API) or [OpenAI Codex](https://openai.com/codex). Then just ask, in plain English:

> *"Audit the citations in `motion-to-dismiss.docx`. Check the cases against CourtListener and tell me which quotes you can't verify."*

The assistant follows DIFTCL's built-in workflow — extract, check form, validate against CourtListener, verify quotes, and report — and hands you a clean summary. **No coding required.**

**→ See [Using DIFTCL in Claude or Codex](#using-diftcl-in-claude-or-codex) for example prompts and a full walkthrough.**

> **Note:** the CourtListener validation step needs a connection. In **Claude**, the easiest path is the **CourtListener MCP connector**; on any host you can instead set a free CourtListener REST token (see [CourtListener validation](#courtlistener-validation)). Everything else works without it.

### 2. As a standalone command-line tool

The `python/` folder contains a small, dependency-light Python program for tech-comfortable lawyers, paralegals, and legal-ops teams who want **repeatable, fully local audits** without setting up an AI workflow. It runs on your machine, reads your files directly, and (for the parts that don't need the internet) never sends anything anywhere.

You can use either mode, or both. The two share the same rules and the same conservative philosophy.

---

## Installation

> **A note on trust.** This is an open-source tool that includes an executable Python helper. As with any third-party software touching client work, review the code and run it in an environment appropriate to your confidentiality obligations.

> **Windows:** the commands below use the macOS/Linux shell. On Windows, run them in **Git Bash**, or use the PowerShell equivalents shown where they differ. Wherever you see `python3`, use `python` or `py` on Windows.

### Claude Code

```bash
# Personal skill (available in every project)
mkdir -p "$HOME/.claude/skills"
git clone --branch v1.0.0-rc.4 https://github.com/DIGITALSON-IT/skill-diftcl.git \
  "$HOME/.claude/skills/diftcl"

# …or project-local (this repo/matter only)
mkdir -p .claude/skills
git clone --branch v1.0.0-rc.4 https://github.com/DIGITALSON-IT/skill-diftcl.git \
  .claude/skills/diftcl
```

Claude Code loads skills from `~/.claude/skills/<name>/SKILL.md`; the folder name should match the skill name (`diftcl`). See the [Claude Code skills docs](https://docs.claude.com/en/docs/claude-code/skills).

### Codex

Codex discovers skills in `~/.agents/skills` (all projects) or a repo's `.agents/skills` folder ([Codex skills docs](https://developers.openai.com/codex/skills)):

```bash
mkdir -p "$HOME/.agents/skills"
git clone --branch v1.0.0-rc.4 https://github.com/DIGITALSON-IT/skill-diftcl.git \
  "$HOME/.agents/skills/diftcl"
```

Restart Codex afterward so it picks up the new skill. (Older Codex versions used `~/.codex/skills`; if `/skills` doesn't list DIFTCL, clone into that path instead.)

### Claude.ai / Claude Console

Package the folder and upload it through the Skills UI in your account or organization:

```bash
git clone --branch v1.0.0-rc.4 https://github.com/DIGITALSON-IT/skill-diftcl.git
cd skill-diftcl
zip -r ../diftcl.zip SKILL.md README.md LICENSE agents python references templates
```

On Windows (PowerShell):

```powershell
git clone --branch v1.0.0-rc.4 https://github.com/DIGITALSON-IT/skill-diftcl.git
cd skill-diftcl
Compress-Archive -Path SKILL.md, README.md, LICENSE, agents, python, references, templates -DestinationPath ..\diftcl.zip
```

### Standalone Python tool

Requires **Python 3.9 or newer** (standard library only — no `pip install` needed):

```bash
git clone --branch v1.0.0-rc.4 https://github.com/DIGITALSON-IT/skill-diftcl.git
cd skill-diftcl
python3 python/diftcl_citation_audit.py --help    # Windows: python python\diftcl_citation_audit.py --help
```

**To audit PDFs**, install `pdftotext` (from Poppler). Word (`.docx`), Markdown, text, and HTML need nothing extra.

```bash
# Debian/Ubuntu
sudo apt-get install poppler-utils
# macOS (Homebrew)
brew install poppler
# Windows (Chocolatey)
choco install poppler
```

> **Scanned PDFs:** if a PDF is a scanned image with no text layer, DIFTCL will tell you it needs OCR rather than silently returning nothing. Run it through an OCR tool first.

---

## Using DIFTCL in Claude or Codex

Once the skill is installed (see [Installation](#installation)), **you don't run any commands — you just ask, in plain English**, and point to the document you want reviewed. Claude or Codex recognizes the request, runs DIFTCL's built-in workflow, and hands back a clean, prioritized summary.

### Give it a document

- **Claude Code / Codex** — reference a file path in your project: *"audit the citations in `briefs/motion-to-dismiss.docx`."*
- **Claude.ai / Claude Desktop** — attach or drag-and-drop the file, then ask.

DIFTCL reads Word, PDF, HTML, Markdown, and plain text.

### Example prompts

Just describe what you need. These map to each capability:

| What you want | What to say |
|---|---|
| **Full citation audit** | *"Use DIFTCL to audit every citation in `brief.docx`. Validate the cases against CourtListener and flag anything that doesn't check out."* |
| **Catch fake or misquoted language** | *"Check whether the quotations in this brief actually appear in the cited opinions, and list any you can't verify."* |
| **Table of Authorities** | *"Pull every case citation out of this PDF and draft a table of authorities with mention counts."* |
| **Statutes & doctrines** | *"Extract the statutes, rules, and legal doctrines in this memo and tell me what to verify and where."* |
| **Deadlines** | *"I was served on June 1. Using the attached scheduling order, calculate when my response is due — show the counting method and holidays."* |
| **Strategy / red-team** | *"Give me a contrarian review of this brief: where would opposing counsel attack the authorities or the quotes?"* |
| **Review packet** | *"Produce a paralegal review packet for `brief.pdf` — prioritized action items only."* |

Keep the conversation going with follow-ups: *"show me only the unverified quotes," "draft corrected versions of the malformed citations," "redo the table of authorities after my edits."*

For a complete legal-team process, see the [Attorney and Paralegal Workflow Guide](references/attorney-paralegal-workflows.md), which includes the matter-review sequence, handoff rules, visual workflow map, and copy-ready prompts for comprehensive and focused reviews.

### What happens under the hood

The assistant extracts the citations, checks their Bluebook form, validates each case against CourtListener (when connected), verifies quotations against the opinion text or a source you provide, and reports every finding as **ok / warning / error / not checked** (see [Understanding the results](#understanding-the-results)). In Claude Code and code-execution environments it may run the bundled Python helper for you — you never have to touch it.

### Turning on CourtListener validation

Case-existence and online quote checks need a connection:

- **Claude** — enable the **CourtListener MCP connector** from Claude's connector directory (easiest), or set a REST token as below.
- **Codex and other hosts** — set a free CourtListener REST token (`export COURTLISTENER_TOKEN="..."`), or configure a CourtListener MCP server if your host supports one.

Without it, DIFTCL still extracts citations, checks form, drafts the TOA, calculates deadlines, and verifies quotes against source text you provide — it simply marks anything that needs the internet as **not checked**.

### If the skill doesn't trigger

Skills usually activate on their own. If it doesn't, name it explicitly: *"use the DIFTCL skill to…"* (or `$diftcl` in Codex).

---

## Using the command-line tool

Prefer to run it yourself? The bundled standalone tool does the same audits locally, no AI required. *(These are the command-line equivalents of the prompts above. On Windows, replace `python3` with `python` or `py`.)*

Audit a Word document and get a readable report:

```bash
python3 python/diftcl_citation_audit.py --input brief.docx
```

Check a single citation:

```bash
python3 python/diftcl_citation_audit.py \
  --text "Brown v. Bd. of Educ., 347 U.S. 483, 495 (1954)."
```

Produce a paralegal/attorney **review packet** (prioritized action items):

```bash
python3 python/diftcl_citation_audit.py --input brief.pdf --output-format review
```

That's it. Everything below is the same idea with more options.

---

## Common tasks, step by step

<details>
<summary><b>Verify that quotes are real</b></summary>

Point DIFTCL at your draft and at the source opinion text, and ask it to check quotations:

```bash
python3 python/diftcl_citation_audit.py \
  --input draft.md \
  --source opinion.txt \
  --verify-quotes
```

Each quotation tied to a citation comes back as **verified**, **not found**, **too short to confirm**, or **not checked** (no source text was available). A real citation does **not** make its quote valid — the two are reported separately.
</details>

<details>
<summary><b>Draft a Table of Authorities</b></summary>

```bash
python3 python/diftcl_citation_audit.py --input brief.docx --toa
```

You get each authority, its citation, the number of mentions, and where they appear — a starting point for the final TOA (page numbers depend on your filed layout).
</details>

<details>
<summary><b>Calculate a filing deadline</b></summary>

DIFTCL never guesses deadlines. You give it the controlling rule; it does the counting.

```bash
python3 python/diftcl_citation_audit.py \
  --calendar-from 2026-06-01 \
  --calendar-rules-file calendar-rules.json \
  --calendar-rule response-after-service
```

Copy `templates/calendar-rules.json` into your matter folder and fill it in from the **actual** scheduling order, local rule, or statute. The result reports the trigger date, day count, holidays, weekend/holiday roll, and a reminder to confirm.
</details>

<details>
<summary><b>Extract statutes, rules, and doctrines</b></summary>

```bash
python3 python/diftcl_citation_audit.py \
  --text "42 U.S.C. § 1983, Fed. R. Civ. P. 12(b)(6), and qualified immunity" \
  --authorities
```

Add `--educate` instead for plain-language "research note" explanations and the official source to check (U.S. Code, eCFR, Congress.gov, and the like).
</details>

<details>
<summary><b>Strategy & contrarian issue-spotting</b></summary>

```bash
python3 python/diftcl_citation_audit.py \
  --input brief.md \
  --strategy \
  --strategy-position defense \
  --strategy-objective "oppose preliminary injunction"
```

Returns separate **Strategy**, **Tactics**, and **Contrarian** notes grounded in what DIFTCL actually found — not invented holdings.
</details>

<details>
<summary><b>Reusable matter settings</b></summary>

Copy `templates/diftcl.yaml` into your working folder as `diftcl.yaml` and set the filing court, jurisdiction, strictness, and preferred output once. DIFTCL picks it up automatically:

```bash
python3 python/diftcl_citation_audit.py --input brief.pdf --config diftcl.yaml --output-format review
```
</details>

<details>
<summary><b>Output formats</b></summary>

Use `--output-format` (or the shortcut flags) to choose how results come back:

| Format | What it is |
|---|---|
| `markdown` *(default)* | Full, readable citation audit with a review summary |
| `review` | Prioritized attorney/paralegal action packet |
| `toa` | Draft Table of Authorities |
| `calendar` | Deadline calculation |
| `strategy` | Strategy / tactics / contrarian notes |
| `authorities` | Statute / rule / regulation / doctrine extraction |
| `education` | Plain-language education notes |
| `json` | Structured data for automation and downstream tools |
</details>

---

## Understanding the results

DIFTCL reports each finding with a clear status so you know what needs a human:

| Status | Meaning |
|---|---|
| ✅ **ok** | Valid and supported as far as DIFTCL can tell. |
| ⚠️ **warning** | A style issue or an unresolved ambiguity — worth a look. |
| ❌ **error** | A missing/invalid citation, or a quote not found in the source. **Fix before filing.** |
| ❔ **not checked** | DIFTCL couldn't verify it (e.g. no source text or no CourtListener access). **Not a clean bill of health.** |

The golden rule: **"not checked" is not "ok."** When DIFTCL can't confirm something, it says so plainly rather than guessing.

---

## CourtListener validation

DIFTCL uses [CourtListener](https://www.courtlistener.com/) — a free, public case-law database from the Free Law Project — to confirm that cited cases exist and to pull opinion text for quote-checking. How you connect depends on where you run it:

- **In Claude** — the easiest path is the **CourtListener MCP connector**: enable it from Claude's connector directory.
- **On any host (Codex, other agents, or the standalone CLI)** — use the **CourtListener REST API** with a free `COURTLISTENER_TOKEN` (or configure a CourtListener MCP server if your host supports MCP):

  ```bash
  export COURTLISTENER_TOKEN="your-token"
  python3 python/diftcl_citation_audit.py --input brief.md --courtlistener --verify-quotes --json
  ```

Either way, the rest of DIFTCL works offline — extraction, citation-form review, Table of Authorities, deadlines, and quote-checking against source text you provide — and anything it can't validate online is clearly marked **not checked**. DIFTCL respects CourtListener's rate limits and does not retry aggressively.

> DIFTCL performs **existence and quote checks**, not Shepard's®/KeyCite®-style negative-treatment analysis. It will not tell you whether a case is still good law.

---

## Confidentiality & data handling

Legal documents are sensitive. DIFTCL is designed to respect that:

- **Run it locally.** Everything except optional CourtListener lookups happens on your machine.
- **Keep client documents out of this repository.** Never commit privileged, sealed, or client-identifying material.
- **Only citations/quotes leave your machine** during a CourtListener check — and only if you enable it. Verify that any online lookup is permitted by the matter's confidentiality requirements.
- **Securely delete your working files when done.** DIFTCL ships a cross-platform secure-delete helper:

```bash
python3 python/diftcl_shred.py ./audit-output           # dry run — lists what would be deleted
python3 python/diftcl_shred.py ./audit-output --yes     # overwrite, then delete
```

`diftcl_shred.py` overwrites files before removing them and refuses dangerous targets (drive roots, very shallow paths). *Note:* on SSDs and modern filesystems, overwriting is not a forensic guarantee — pair it with full-disk encryption for stronger assurance.

---

## Important: Not Legal Advice

**DIFTCL is a research and quality-control aid. It is not a lawyer, and it does not give legal advice.**

- It does **not** decide whether a case supports your proposition, whether a quote is persuasive, or whether an authority is still good law.
- Its citation-form checks are **Bluebook-style heuristics**, not a guarantee of compliance with your court's local rules.
- Its deadline calculations are only as good as the rule **you** supply, and must be confirmed against the controlling order and calendar.
- Its strategy and education output is **issue-spotting for a human reviewer**, never a conclusion.
- Automated tools can miss things and can be wrong.

**A licensed attorney must review everything before it is filed, served, or relied upon.** Use of DIFTCL does not create an attorney-client relationship and comes with no warranty (see [LICENSE](LICENSE)).

---

## Current limitations

- Focuses on **U.S. case citations**; statutes, regulations, and law-review cites are extracted and pointed to official sources but not fully validated.
- `Id.` and `supra` are **flagged for a human to map**, not auto-resolved.
- CourtListener checks require API access or the AI-skill integration.
- Table-of-Authorities output is a **draft input** — final page numbers depend on your filed layout.
- No Shepard's/KeyCite-style negative-treatment analysis.
- Quote verification confirms **text presence**, not legal relevance or persuasiveness.

---

## Roadmap

- Short-form resolution for `Id.`, `supra`, and abbreviated case references
- Pincite-level quote verification
- DOCX comment output for in-document attorney/paralegal review
- Authority-quality flags (unpublished, nonprecedential, potentially stale)
- Jurisdiction rule packs populated from user-approved official sources
- Reusable, hashed audit-evidence bundles with source IDs and offsets

See [CHANGELOG.md](CHANGELOG.md) for what's shipped.

---

## Contributing

Contributions are welcome — bug reports, citation-format edge cases, new state-reporter coverage, and documentation improvements especially.

- The skill's behavior lives in `SKILL.md` and the `references/` notes; the standalone tool lives in `python/`.
- Run the test suite before sending changes:
  ```bash
  python3 python/run_regression_smoke.py
  ```
- Please **do not** include real client documents, privileged material, or copyrighted reporter/Bluebook text in issues, pull requests, or test fixtures. Use redacted or synthetic examples.

---

## License

Released under the [GNU Affero General Public License v3.0 or later](LICENSE)
(`AGPL-3.0-or-later`). Copyright © 2026 DigitalsonIT.

Commercial licensing is available from Digitalson for organizations that need
terms outside the AGPL.

---

## About

This skill is built and released openly by **Digitalson** — the team behind **DIFTCL — Do It For The Case Law**, an **educational AI news service** that showcases the real-world capabilities of AI through neutral, accessible coverage of U.S. federal appellate court decisions ([doitforthecaselaw.com](https://doitforthecaselaw.com)).

We build tools like this in the open to help the legal industry put emerging technology to work **safely and responsibly** — automation, research workflows, and data validation, always with human review where professional judgment is required.

> **Digitalson is your go-to legal technology enablement partner.** Want help bringing AI and automation into your firm or legal-ops team? Reach out at **[digitalson.com](https://digitalson.com)**.

<div align="center">
<sub>Produced by <b>Digitalson</b> · <b>DIFTCL — Do It For The Case Law</b>. Built for the people who actually check the citations. ⚖️</sub>
</div>
