#!/usr/bin/env python3
"""Extract and audit U.S. case citations and nearby quotes.

The script is intentionally dependency-light for agent containers. It uses
stdlib text extraction for TXT/MD/HTML/DOCX and optional system pdftotext for
PDFs. CourtListener validation uses the public REST API when requested.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

# On Windows, piped stdout/stderr default to the legacy code page, which mangles
# characters like the section symbol into mojibake for downstream consumers.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass


COURTLISTENER_LOOKUP = "https://www.courtlistener.com/api/rest/v4/citation-lookup/"
RULE_SOURCE_REGISTRY = Path(__file__).resolve().parents[1] / "references" / "court-rule-source-registry.json"
DOCTRINE_GLOSSARY = Path(__file__).resolve().parents[1] / "templates" / "doctrine-glossary.json"
MAX_LOOKUP_CHARS = 64000
QUOTE_WINDOW = 900
DEFAULT_MIN_QUOTE_CHARS = 24

REPORTER_FIXES = {
    "US": "U.S.",
    "U. S.": "U.S.",
    "S.Ct.": "S. Ct.",
    "SCt": "S. Ct.",
    "L.Ed.2d": "L. Ed. 2d",
    "LEd2d": "L. Ed. 2d",
    "F2d": "F.2d",
    "F3d": "F.3d",
    "F4th": "F.4th",
    "F.Supp.": "F. Supp.",
    "F.Supp.2d": "F. Supp. 2d",
    "F.Supp.3d": "F. Supp. 3d",
}

# Reporter abbreviations recognized in citations, grouped for maintainability:
# federal, regional (West) reporters, then state/territory official reporters with
# common appellate-court variants. Multi-token reporters (e.g. "N.Y.S.") are listed
# before their shorter prefixes (e.g. "N.Y.") so the longer alternative wins.
# Separators inside reporters use \s* (not a literal optional space) so that PDF
# line-wrapping — e.g. "Ga.\nApp." or "F.\nSupp." — still matches. Regex
# backtracking preserves the whitespace that separates the reporter from the page.
_FEDERAL_REPORTERS = [
    r"U\.\s*S\.", r"US", r"S\.\s*Ct\.", r"S\.Ct\.", r"L\.\s*Ed\.(?:\s*2d)?", r"L\.Ed\.(?:2d)?",
    r"F\.\s*Supp\.\s*(?:2d|3d)?", r"F\.Supp\.(?:2d|3d)?",
    r"F\.\s*(?:2d|3d|4th)?", r"F2d", r"F3d", r"F4th",
    r"Fed\.\s*App'?x\.?", r"F\.\s*App'x\.?",
]
_REGIONAL_REPORTERS = [
    r"N\.E\.\s*(?:2d|3d)?", r"N\.W\.\s*(?:2d|3d)?", r"S\.E\.\s*(?:2d|3d)?",
    r"S\.W\.\s*(?:2d|3d)?", r"So\.\s*(?:2d|3d)?", r"N\.Y\.S\.\s*(?:2d|3d)?",
    r"P\.\s*(?:2d|3d)?", r"A\.\s*(?:2d|3d)?",
]
# State and territory official reporters. Kept explicit (rather than a generic
# "Word." matcher) to avoid false positives on ordinary abbreviations in prose.
_STATE_REPORTERS = [
    r"Ga\.(?:\s*App\.)?", r"Cal\.(?:\s*App\.|\s*Rptr\.)?(?:\s*(?:2d|3d|4th|5th))?",
    r"N\.Y\.(?:\s*(?:2d|3d))?", r"Ill\.(?:\s*App\.|\s*Dec\.)?(?:\s*(?:2d|3d))?",
    r"Mass\.(?:\s*App\.(?:\s*Ct\.)?)?", r"Pa\.(?:\s*Super\.|\s*Commw\.)?(?:\s*(?:2d|3d))?",
    r"Tex\.(?:\s*Crim\.\s*App\.|\s*Civ\.\s*App\.|\s*App\.)?", r"Fla\.(?:\s*App\.)?",
    r"N\.J\.(?:\s*Super\.)?", r"Ohio(?:\s*St\.|\s*App\.)?(?:\s*(?:2d|3d))?",
    r"Va\.(?:\s*App\.)?", r"Md\.(?:\s*App\.)?", r"Mich\.(?:\s*App\.)?",
    r"Wash\.(?:\s*App\.)?(?:\s*2d)?", r"Conn\.(?:\s*App\.)?", r"Wis\.(?:\s*2d)?",
    r"Minn\.(?:\s*App\.)?", r"Mo\.(?:\s*App\.)?", r"Tenn\.(?:\s*Crim\.\s*App\.|\s*App\.)?",
    r"N\.C\.(?:\s*App\.)?", r"S\.C\.", r"Ala\.(?:\s*(?:Civ|Crim)\.\s*App\.)?",
    r"Ky\.(?:\s*App\.)?", r"La\.(?:\s*App\.)?", r"Ariz\.(?:\s*App\.)?",
    r"Colo\.(?:\s*App\.)?", r"Or\.(?:\s*App\.)?", r"Kan\.(?:\s*App\.)?(?:\s*2d)?",
    r"Ind\.(?:\s*App\.)?", r"Iowa", r"Okla\.(?:\s*Crim\.)?", r"Ark\.(?:\s*App\.)?",
    r"Miss\.", r"Nev\.", r"Utah(?:\s*2d)?", r"Idaho", r"Mont\.", r"Haw\.(?:\s*App\.)?",
    r"Neb\.(?:\s*App\.)?", r"N\.M\.(?:\s*App\.)?", r"W\.\s*Va\.", r"R\.I\.", r"N\.H\.",
    r"Me\.", r"Vt\.", r"Del\.(?:\s*Ch\.)?", r"S\.D\.", r"N\.D\.", r"Wyo\.",
    r"Alaska", r"D\.C\.",
]
REPORTER_PATTERN = r"(?:" + "|".join(
    _FEDERAL_REPORTERS + _REGIONAL_REPORTERS + _STATE_REPORTERS
) + r")"

# A case-name party is a capitalized token followed by more capitalized tokens
# or a small set of lowercase connectors. Constraining the tokens this way keeps
# the name from swallowing a preceding prose lead-in such as
# "As the court explained in ..." before the real party name.
_PARTY_TOKEN = r"[A-Z][A-Za-z0-9&.'’]*"
_PARTY_CONNECTOR = r"(?:of|the|and|for|in|on|an?|&|ex|rel\.|re|et|al\.|de|la|von|van|der|los)"
# Party-name steps: a normal space/hyphen-joined token or connector, or a
# comma-joined corporate suffix ("Under Armour, Inc."). The comma form requires a
# capitalized token (never a digit) so it cannot swallow the name/volume comma.
PARTY_PATTERN = (
    rf"{_PARTY_TOKEN}"
    rf"(?:[-\s]+(?:{_PARTY_TOKEN}|{_PARTY_CONNECTOR})|,\s+{_PARTY_TOKEN}){{0,20}}"
)
CASENAME_PATTERN = rf"{PARTY_PATTERN}(?:\s+(?:v\.|vs\.)\s+{PARTY_PATTERN})*"

# A pincite page number. The trailing (?!\d) forces the whole number to be
# consumed so a following negative lookahead cannot be defeated by the regex
# engine backtracking to a shorter digit run.
_PIN_NUM = r"\*?\d{1,5}(?!\d)"

# Shared citation tail: optional pincite, optional parallel reporter citation(s),
# an optional missing-comma pincite (a bare page number before the parenthetical),
# and an optional court/year parenthetical. The pincite must not consume the
# volume of a following parallel citation (negative lookahead on the reporter).
CITE_TAIL = (
    r"(?P<pincite>"
    rf"(?:\s*,\s*(?:at\s+)?{_PIN_NUM}(?!\s+{REPORTER_PATTERN})"
    rf"(?:\s*[-,]\s*{_PIN_NUM}(?!\s+{REPORTER_PATTERN}))*)"
    rf"|(?:\s+at\s+{_PIN_NUM}(?:\s*[-,]\s*{_PIN_NUM})*)"
    r")?"
    rf"(?P<parallel>(?:\s*,\s*\d{{1,4}}\s+{REPORTER_PATTERN}\s+\d{{1,5}}"
    rf"(?:\s*,\s*(?:at\s+)?{_PIN_NUM})?)*)"
    r"(?P<badpincite>\s+\d{1,5}(?=\s*\())?"
    r"\s*(?P<paren>\([^)]*\))?"
)

CASE_CITE_RE = re.compile(
    rf"(?P<case>{PARTY_PATTERN}\s+(?:v\.|vs\.)\s+{PARTY_PATTERN}),\s*"
    rf"(?P<volume>\d{{1,4}})\s+(?P<reporter>{REPORTER_PATTERN})\s+"
    rf"(?P<page>\d{{1,5}})"
    rf"{CITE_TAIL}"
)

BARE_CITE_RE = re.compile(
    rf"(?<![A-Za-z])(?P<volume>\d{{1,4}})\s+(?P<reporter>{REPORTER_PATTERN})\s+"
    rf"(?P<page>\d{{1,5}})"
    rf"{CITE_TAIL}",
    re.IGNORECASE,
)

WL_LEXIS_RE = re.compile(
    r"(?P<year>\d{4})\s+(?P<service>WL|U\.S\. App\. LEXIS|U\.S\. Dist\. LEXIS)\s+"
    r"(?P<number>\d+)(?P<pincite>,\s+at\s+\*\d+(?:[-,]\s*\*\d+)*)?"
    r"\s*(?P<paren>\([^)]*\))?",
    re.IGNORECASE,
)

QUOTE_RE = re.compile(r"\"([^\"\n]{8,500})\"|“([^”\n]{8,500})”|‘([^’\n]{8,500})’")
ID_RE = re.compile(r"\b[Ii]d\.(?:\s+at\s+\*?\d{1,5}(?:[-,]\s*\*?\d{1,5})*)?")
SUPRA_RE = re.compile(
    rf"(?P<label>{CASENAME_PATTERN}),\s+supra(?:,\s+at\s+{_PIN_NUM})?"
)
USC_RE = re.compile(
    r"\b(?P<title>\d+)\s+U\.?\s*S\.?\s*C\.?(?:A\.)?\s*"
    r"(?:§{1,2}|sec\.?|section|sections?)\s*"
    r"(?P<section>[A-Za-z0-9][A-Za-z0-9\-.:()]*)",
    re.IGNORECASE,
)
CFR_RE = re.compile(
    r"\b(?P<title>\d+)\s+C\.?\s*F\.?\s*R\.?\s*"
    r"(?:§{1,2}|sec\.?|section|sections?)\s*"
    r"(?P<section>[A-Za-z0-9][A-Za-z0-9\-.:()]*)",
    re.IGNORECASE,
)
FED_RULE_RE = re.compile(
    r"\bFed\.?\s+R\.?\s+(?P<rule_type>Civ\.?\s*P\.?|Crim\.?\s*P\.?|Evid\.?|App\.?\s*P\.?|Bankr\.?\s*P\.?)\s*"
    r"(?P<rule>[0-9]+(?:\([a-z0-9]+\))*)",
    re.IGNORECASE,
)
STATE_STATUTE_RE = re.compile(
    r"\b(?P<jurisdiction>[A-Z][a-z]{2,}|[A-Z]{2})\.?\s+"
    r"(?P<code>Stat\.|Code|Rev\. Stat\.|Gen\. Stat\.|Civ\. Code|Penal Code|Admin\. Code)\s*"
    r"(?:§{1,2}|sec\.?|section|sections?)\s*"
    r"(?P<section>[A-Za-z0-9][A-Za-z0-9\-.:()]*)",
)
CONSTITUTION_RE = re.compile(
    r"\b(?:(?P<us>U\.?\s*S\.?)\s+Const\.?|(?P<state>[A-Z][a-z]+)\s+Const\.?)\s*"
    r"(?P<provision>(?:art\.|article|amend\.|amendment)\s+[A-Za-z0-9IVXLCivxlc.]+(?:,\s*§+\s*[A-Za-z0-9().-]+)?)",
    re.IGNORECASE,
)


@dataclass
class MatterConfig:
    filing_court: str = ""
    jurisdiction: str = ""
    document_type: str = ""
    strict: bool = False
    courtlistener: bool = False
    verify_quotes: bool = False
    quote_min_chars: int = DEFAULT_MIN_QUOTE_CHARS
    require_quote_pincites: bool = True
    require_parenthetical_court: bool = False
    local_rules_enabled: bool = False
    local_rules_court_id: str = ""
    local_rules_url: str = ""
    local_rules_cache_ttl_days: int = 30
    local_rules_max_requests: int = 3
    local_rules_retry_limit: int = 0
    local_rules_min_delay_seconds: int = 3
    calendar_enabled: bool = False
    calendar_rules_file: str = ""
    calendar_holidays: list[str] = field(default_factory=list)
    strategy_enabled: bool = False
    strategy_position: str = "neutral"
    strategy_objective: str = ""
    doctrine_education_enabled: bool = False
    doctrine_glossary_file: str = ""
    output_format: str = "markdown"


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    suggestion: str = ""


@dataclass
class Citation:
    text: str
    start: int
    end: int
    kind: str
    volume: str = ""
    reporter: str = ""
    page: str = ""
    case_name: str = ""
    pincite: str = ""
    parenthetical: str = ""
    source_page: int = 1
    source_line: int = 1
    findings: list[Finding] = field(default_factory=list)
    courtlistener: dict[str, Any] | None = None
    nearby_quotes: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ShortReference:
    text: str
    start: int
    end: int
    kind: str
    source_page: int
    source_line: int
    status: str
    message: str
    target: str = ""


@dataclass
class AuthorityMention:
    text: str
    start: int
    end: int
    kind: str
    source_page: int
    source_line: int
    normalized: str = ""
    source_hint: str = ""
    status: str = "extracted"
    note: str = ""


@dataclass
class DoctrineMention:
    doctrine_id: str
    term: str
    start: int
    end: int
    source_page: int
    source_line: int
    plain_language: str = ""
    research_questions: list[str] = field(default_factory=list)
    status: str = "issue_spotted"


def strip_html(value: str) -> str:
    value = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return html.unescape(re.sub(r"\s+", " ", value)).strip()


def read_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        data = zf.read("word/document.xml")
    root = ElementTree.fromstring(data)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for para in root.findall(".//w:p", ns):
        parts = [node.text or "" for node in para.findall(".//w:t", ns)]
        if parts:
            paragraphs.append("".join(parts))
    return "\n".join(paragraphs)


class ExtractionError(RuntimeError):
    """Raised when a document's text cannot be extracted. Catchable so that
    batch callers can skip an unreadable file instead of aborting the run."""


def read_pdf(path: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout
    except FileNotFoundError as exc:
        raise ExtractionError(
            "PDF extraction requires the 'pdftotext' command (poppler-utils) in PATH. "
            "Install poppler, or convert the PDF to text/DOCX first."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise ExtractionError(
            f"pdftotext could not read {path.name}. The PDF may be encrypted, corrupt, "
            f"or a scanned image with no text layer (OCR required). Details: "
            f"{(exc.stderr or '').strip()[:200]}"
        ) from exc


def read_input(args: argparse.Namespace) -> str:
    chunks: list[str] = []
    if args.text:
        chunks.append(args.text)
    if args.cite:
        chunks.append(args.cite)
    if args.input:
        path = Path(args.input)
        suffix = path.suffix.lower()
        if suffix == ".docx":
            chunks.append(read_docx(path))
        elif suffix == ".pdf":
            chunks.append(read_pdf(path))
        elif suffix in {".html", ".htm"}:
            chunks.append(strip_html(path.read_text(encoding="utf-8", errors="replace")))
        else:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    if not chunks and not sys.stdin.isatty():
        chunks.append(sys.stdin.read())
    if not chunks:
        raise SystemExit("Provide --input, --text, --cite, or stdin.")
    return "\n".join(chunks)


def read_path_text(path_value: str) -> str:
    path = Path(path_value)
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return read_docx(path)
    if suffix == ".pdf":
        return read_pdf(path)
    if suffix in {".html", ".htm"}:
        return strip_html(path.read_text(encoding="utf-8", errors="replace"))
    return path.read_text(encoding="utf-8", errors="replace")


def load_rule_source_registry() -> dict[str, Any]:
    return json.loads(RULE_SOURCE_REGISTRY.read_text(encoding="utf-8"))


def load_doctrine_glossary(path_value: str | None = None) -> dict[str, Any]:
    path = Path(path_value) if path_value else DOCTRINE_GLOSSARY
    return json.loads(path.read_text(encoding="utf-8"))


def filter_rule_sources(registry: dict[str, Any], query: str) -> dict[str, Any]:
    if not query:
        return registry
    needle = query.lower()
    filtered: dict[str, Any] = {"metadata": registry.get("metadata", {})}
    for section in ("federal_directories", "state_judiciary_portals", "territory_judiciary_portals"):
        filtered[section] = [
            item
            for item in registry.get(section, [])
            if needle in item.get("id", "").lower()
            or needle in item.get("name", "").lower()
            or needle in item.get("url", "").lower()
        ]
    return filtered


def format_rule_sources(registry: dict[str, Any]) -> str:
    lines = ["# DIFTCL Court Rule Source Registry", ""]
    metadata = registry.get("metadata") or {}
    if metadata.get("last_reviewed"):
        lines.append(f"Last reviewed: {metadata['last_reviewed']}")
    if metadata.get("use_policy"):
        lines += ["", metadata["use_policy"], ""]
    sections = [
        ("Federal Directories", "federal_directories"),
        ("State Judiciary Portals", "state_judiciary_portals"),
        ("Territory Judiciary Portals", "territory_judiciary_portals"),
    ]
    for title, key in sections:
        items = registry.get(key) or []
        if not items:
            continue
        lines += [f"## {title}", ""]
        for item in items:
            scope = f" - {item['scope']}" if item.get("scope") else ""
            lines.append(f"- `{item['id']}` {item['name']}: {item['url']}{scope}")
        lines.append("")
    return "\n".join(lines)


def parse_iso_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise SystemExit(f"Invalid date '{value}'. Use YYYY-MM-DD.") from exc


def load_calendar_rules(path_value: str | None) -> dict[str, Any]:
    if not path_value:
        return {"rules": [], "holidays": []}
    path = Path(path_value)
    if not path.exists():
        raise SystemExit(f"Calendar rules file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def find_calendar_rule(rules_data: dict[str, Any], rule_id: str) -> dict[str, Any]:
    for rule in rules_data.get("rules") or []:
        if str(rule.get("id")) == rule_id:
            return dict(rule)
    available = ", ".join(str(rule.get("id")) for rule in rules_data.get("rules") or [])
    raise SystemExit(f"Calendar rule '{rule_id}' not found. Available rules: {available or 'none'}")


def is_business_day(day: date, holidays: set[date]) -> bool:
    return day.weekday() < 5 and day not in holidays


def shift_business_days(start: date, days: int, direction: str, holidays: set[date], include_start: bool) -> date:
    step = 1 if direction == "after" else -1
    current = start if include_start else start + timedelta(days=step)
    remaining = days
    if include_start and is_business_day(current, holidays):
        remaining -= 1
    while remaining > 0:
        if is_business_day(current, holidays):
            remaining -= 1
            if remaining == 0:
                break
        current += timedelta(days=step)
    return current


def roll_deadline(day: date, roll: str, holidays: set[date]) -> date:
    if roll == "none" or is_business_day(day, holidays):
        return day
    if roll == "previous_business":
        while not is_business_day(day, holidays):
            day -= timedelta(days=1)
        return day
    while not is_business_day(day, holidays):
        day += timedelta(days=1)
    return day


def calculate_deadline(
    trigger_date: date,
    days: int,
    count: str,
    direction: str,
    roll: str,
    holidays: set[date],
    include_trigger_day: bool,
) -> tuple[date, date]:
    if count == "business":
        raw = shift_business_days(trigger_date, days, direction, holidays, include_trigger_day)
    else:
        step = 1 if direction == "after" else -1
        offset = days - 1 if include_trigger_day else days
        raw = trigger_date + timedelta(days=step * offset)
    return raw, roll_deadline(raw, roll, holidays)


def calendar_from_args(args: argparse.Namespace, cfg: MatterConfig) -> dict[str, Any]:
    rules_data = load_calendar_rules(args.calendar_rules_file or cfg.calendar_rules_file)
    rule: dict[str, Any]
    if args.calendar_rule:
        rule = find_calendar_rule(rules_data, args.calendar_rule)
    else:
        rule = {
            "id": "ad-hoc",
            "label": "Ad hoc deadline",
            "days": args.calendar_days,
            "count": args.calendar_count,
            "direction": args.calendar_direction,
            "roll": args.calendar_roll,
            "include_trigger_day": args.calendar_include_trigger_day,
            "authority": "",
            "notes": "Ad hoc calculation; no jurisdiction rule selected.",
        }
    if rule.get("days") is None:
        raise SystemExit("Calendar calculation requires --calendar-days or a rule with days.")
    trigger_date = parse_iso_date(args.calendar_from)
    holiday_values = list(rules_data.get("holidays") or []) + list(cfg.calendar_holidays)
    if args.calendar_holidays:
        holiday_values += [part.strip() for part in args.calendar_holidays.split(",") if part.strip()]
    holidays = {parse_iso_date(str(value)) for value in holiday_values if str(value).strip()}
    raw, deadline = calculate_deadline(
        trigger_date=trigger_date,
        days=int(rule.get("days")),
        count=str(rule.get("count") or "calendar"),
        direction=str(rule.get("direction") or "after"),
        roll=str(rule.get("roll") or "next_business"),
        holidays=holidays,
        include_trigger_day=bool(rule.get("include_trigger_day", False)),
    )
    return {
        "trigger_date": trigger_date.isoformat(),
        "jurisdiction": rules_data.get("jurisdiction") or cfg.jurisdiction,
        "court": rules_data.get("court") or cfg.filing_court,
        "source_url": rules_data.get("source_url", ""),
        "source_retrieved": rules_data.get("source_retrieved", ""),
        "rule": rule,
        "raw_deadline": raw.isoformat(),
        "deadline": deadline.isoformat(),
        "rolled": raw != deadline,
        "holidays_used": sorted(day.isoformat() for day in holidays),
        "status": "configured_rule" if args.calendar_rule else "not_authoritative",
        "warning": "Confirm the controlling rule, service method, court holidays, and any judge/scheduling order before relying on this deadline.",
    }


def calendar_report(result: dict[str, Any]) -> str:
    rule = result.get("rule") or {}
    lines = ["# DIFTCL Deadline Calculation", ""]
    lines.append(f"- Trigger date: {result['trigger_date']}")
    lines.append(f"- Rule: {rule.get('id')} - {rule.get('label', '')}".rstrip())
    if result.get("court"):
        lines.append(f"- Court: {result['court']}")
    if result.get("jurisdiction"):
        lines.append(f"- Jurisdiction: {result['jurisdiction']}")
    lines.append(f"- Count: {rule.get('days')} {rule.get('count', 'calendar')} day(s), {rule.get('direction', 'after')}")
    lines.append(f"- Include trigger day: {bool(rule.get('include_trigger_day', False))}")
    lines.append(f"- Roll rule: {rule.get('roll', 'next_business')}")
    if result.get("source_url"):
        lines.append(f"- Source: {result['source_url']}")
    lines.append(f"- Raw deadline: {result['raw_deadline']}")
    lines.append(f"- Final deadline: {result['deadline']}")
    if result.get("rolled"):
        lines.append("- Weekend/holiday roll applied: yes")
    if result.get("holidays_used"):
        lines.append(f"- Holidays used: {', '.join(result['holidays_used'])}")
    lines += ["", f"WARNING: {result['warning']}"]
    return "\n".join(lines)


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_config(path: Path) -> dict[str, Any]:
    """Parse a small YAML-like matter config without third-party dependencies."""
    data: dict[str, Any] = {}
    if not path.exists():
        return data
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line or line.startswith("-"):
            continue
        key, value = line.split(":", 1)
        key = key.strip().replace("-", "_")
        value = value.strip().strip("\"'")
        if not value:
            data[key] = ""
        elif value.lower() in {"true", "false", "yes", "no", "on", "off"}:
            data[key] = parse_bool(value)
        elif re.fullmatch(r"\d+", value):
            data[key] = int(value)
        elif value.startswith("[") and value.endswith("]"):
            data[key] = [part.strip().strip("\"'") for part in value[1:-1].split(",") if part.strip()]
        else:
            data[key] = value
    return data


def build_config(args: argparse.Namespace) -> MatterConfig:
    config_path = Path(args.config) if args.config else Path("diftcl.yaml")
    raw = parse_config(config_path) if config_path.exists() else {}
    cfg = MatterConfig(
        filing_court=str(raw.get("filing_court") or raw.get("court") or ""),
        jurisdiction=str(raw.get("jurisdiction") or ""),
        document_type=str(raw.get("document_type") or raw.get("document") or ""),
        strict=bool(raw.get("strict", False)),
        courtlistener=bool(raw.get("courtlistener", False)),
        verify_quotes=bool(raw.get("verify_quotes", False)),
        quote_min_chars=int(raw.get("quote_min_chars", DEFAULT_MIN_QUOTE_CHARS)),
        require_quote_pincites=bool(raw.get("require_quote_pincites", True)),
        require_parenthetical_court=bool(raw.get("require_parenthetical_court", False)),
        local_rules_enabled=bool(raw.get("local_rules_enabled", False)),
        local_rules_court_id=str(raw.get("local_rules_court_id") or ""),
        local_rules_url=str(raw.get("local_rules_url") or ""),
        local_rules_cache_ttl_days=int(raw.get("local_rules_cache_ttl_days", 30)),
        local_rules_max_requests=int(raw.get("local_rules_max_requests", 3)),
        local_rules_retry_limit=int(raw.get("local_rules_retry_limit", 0)),
        local_rules_min_delay_seconds=int(raw.get("local_rules_min_delay_seconds", 3)),
        calendar_enabled=bool(raw.get("calendar_enabled", False)),
        calendar_rules_file=str(raw.get("calendar_rules_file") or ""),
        calendar_holidays=[str(item) for item in raw.get("calendar_holidays", [])],
        strategy_enabled=bool(raw.get("strategy_enabled", False)),
        strategy_position=str(raw.get("strategy_position") or "neutral"),
        strategy_objective=str(raw.get("strategy_objective") or ""),
        doctrine_education_enabled=bool(raw.get("doctrine_education_enabled", False)),
        doctrine_glossary_file=str(raw.get("doctrine_glossary_file") or ""),
        output_format=str(raw.get("output_format") or "markdown"),
    )
    for key in ("filing_court", "jurisdiction", "document_type", "output_format"):
        value = getattr(args, key, None)
        if value:
            setattr(cfg, key, value)
    if args.strict is not None:
        cfg.strict = args.strict
    if args.courtlistener is not None:
        cfg.courtlistener = args.courtlistener
    if args.verify_quotes is not None:
        cfg.verify_quotes = args.verify_quotes
    if args.quote_min_chars is not None:
        cfg.quote_min_chars = args.quote_min_chars
    if getattr(args, "local_rules_enabled", None) is not None:
        cfg.local_rules_enabled = args.local_rules_enabled
    if getattr(args, "local_rules_court_id", None):
        cfg.local_rules_court_id = args.local_rules_court_id
    if getattr(args, "local_rules_url", None):
        cfg.local_rules_url = args.local_rules_url
    if getattr(args, "calendar_rules_file", None):
        cfg.calendar_rules_file = args.calendar_rules_file
    if getattr(args, "strategy_position", None):
        cfg.strategy_position = args.strategy_position
    if getattr(args, "strategy_objective", None):
        cfg.strategy_objective = args.strategy_objective
    if getattr(args, "doctrine_glossary", None):
        cfg.doctrine_glossary_file = args.doctrine_glossary
    if args.toa:
        cfg.output_format = "toa"
    if getattr(args, "calendar_from", None):
        cfg.calendar_enabled = True
    if getattr(args, "strategy", None):
        cfg.strategy_enabled = True
        cfg.output_format = "strategy"
    if getattr(args, "authorities", None):
        cfg.output_format = "authorities"
    if getattr(args, "educate", None):
        cfg.doctrine_education_enabled = True
        cfg.output_format = "education"
    # --json wins over mode shortcuts so e.g. `--authorities --json` emits JSON.
    if args.json:
        cfg.output_format = "json"
    if getattr(args, "output_format", None):
        cfg.output_format = args.output_format
    return cfg


def normalize_quote(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", value.lower())).strip()


def canonical_reporter(reporter: str) -> str:
    compact = re.sub(r"\s+", " ", reporter).strip()
    return REPORTER_FIXES.get(compact, REPORTER_FIXES.get(compact.replace(" ", ""), compact))


def add(finds: list[Finding], severity: str, code: str, message: str, suggestion: str = "") -> None:
    finds.append(Finding(severity, code, message, suggestion))


def style_audit(cite: Citation, cfg: MatterConfig | None = None) -> None:
    cfg = cfg or MatterConfig()
    text = cite.text
    if "vs." in text.lower():
        add(cite.findings, "error", "case_vs", "Case citations should use 'v.', not 'vs.'.")
    if cite.case_name and re.search(r"\bU\.S\.\s+(?:v\.|vs\.)", cite.case_name, re.I):
        add(
            cite.findings,
            "error",
            "us_party_abbrev",
            "Do not abbreviate United States as U.S. when it is a party name.",
            re.sub(r"\bU\.S\.\s+(?:v\.|vs\.)", "United States v.", cite.case_name, flags=re.I),
        )
    canon = canonical_reporter(cite.reporter)
    if cite.reporter and canon != re.sub(r"\s+", " ", cite.reporter).strip():
        add(
            cite.findings,
            "warning",
            "reporter_normalization",
            f"Reporter abbreviation appears noncanonical: {cite.reporter}.",
            canon,
        )
    if cite.kind == "case" and not cite.parenthetical:
        add(cite.findings, "error", "missing_parenthetical", "Missing court/year parenthetical.")
    if cite.parenthetical and not re.search(r"\b(17|18|19|20)\d{2}\b", cite.parenthetical):
        add(cite.findings, "error", "missing_year", "Parenthetical should include a decision year.")
    if cfg.require_parenthetical_court and cite.parenthetical:
        if cite.reporter.upper().replace(" ", "") not in {"U.S.", "US"}:
            if not re.search(r"(Cir\.|D\.|App\.|Ct\.|Dist\.|Sup\.|[A-Z][a-z]{2,}\.)", cite.parenthetical):
                add(
                    cite.findings,
                    "warning",
                    "missing_court",
                    "Configured matter requires court information in parentheticals.",
                    cfg.filing_court,
                )
    if cite.reporter.upper().replace(" ", "") in {"U.S.", "US"} and cite.parenthetical:
        if re.search(r"(Cir\.|D\.|App\.|Ct\.|Dist\.|Sup\. Ct\.)", cite.parenthetical):
            add(
                cite.findings,
                "warning",
                "scotus_parenthetical",
                "U.S. reporter Supreme Court citations usually need only the year in the parenthetical.",
            )
    if re.search(r"\d+\s+" + REPORTER_PATTERN + r"\s+\d+\s+at\s+\d+", text, re.I):
        add(
            cite.findings,
            "warning",
            "ordinary_pincite_at",
            "Ordinary reporter page pincites usually use a comma, not 'at'.",
        )
    if cite.parenthetical and re.search(r"\b(1st|2nd|3rd|[4-9]th|1[0-9]th|[2-9][0-9]th)\s+Cir\.", cite.parenthetical):
        add(
            cite.findings,
            "warning",
            "circuit_ordinal",
            "Circuit ordinals in citations should use legal ordinal form such as 2d or 3d, not 2nd or 3rd.",
        )
    if cite.kind == "wl_lexis" and cite.pincite and "at *" not in cite.pincite:
        add(cite.findings, "warning", "star_pincite", "WL/LEXIS pincites should use 'at *N'.")
    if cite.kind == "wl_lexis":
        add(
            cite.findings,
            "warning",
            "unpublished_electronic_cite",
            "WL/LEXIS citations often require extra review for unpublished/nonprecedential status and local rules.",
        )
    if cfg.strict and cite.kind in {"case", "bare"} and not cite.pincite:
        add(
            cite.findings,
            "warning",
            "strict_missing_pincite",
            "Strict review is enabled; add a pincite when citing a specific proposition.",
        )


def source_page(text: str, offset: int) -> int:
    return text.count("\f", 0, offset) + 1


def source_line(text: str, offset: int) -> int:
    page_start = text.rfind("\f", 0, offset) + 1
    return text.count("\n", page_start, offset) + 1


# Capitalized words that commonly precede a case name at the start of a sentence
# or after a signal but are not part of the party name. They are trimmed from the
# front of a captured case name. "The"/"Of"/"And"/"For"/"Under"/"Compare" are
# deliberately excluded because they can be the real first word of a party name.
_LEADIN_WORDS = {
    "see", "cf", "cf.", "accord", "but", "thus", "indeed", "however", "moreover",
    "also", "quoting", "citing", "later", "recently", "finally", "in", "as",
    "here", "where", "when", "while", "after", "before",
}
# Multi-word name openers that must be preserved even though they start with a
# trimmable word (e.g. "In re", "Ex parte").
_NAME_OPENERS = ("in re", "ex parte", "ex rel.", "in the matter", "in the estate", "in the interest")


def trim_case_name(name: str) -> str:
    if not name:
        return name
    words = name.split()
    index = 0
    while index < len(words) - 1:
        remaining = " ".join(words[index:]).lower()
        if remaining.startswith(_NAME_OPENERS):
            break
        if words[index].lower().strip(",.") not in _LEADIN_WORDS:
            break
        index += 1
    return " ".join(words[index:])


def _ws(value: str) -> str:
    """Collapse internal whitespace (incl. PDF line-wrap newlines) for display."""
    return re.sub(r"\s+", " ", value or "").strip()


def _citation_from_match(match: re.Match[str], kind: str, text: str) -> Citation:
    groups = match.groupdict()
    pincite = _ws(groups.get("pincite") or "")
    bad_pincite = groups.get("badpincite")
    if bad_pincite and not pincite:
        # A bare page number before the parenthetical is a missing-comma pincite.
        pincite = _ws(bad_pincite)
    return Citation(
        text=_ws(match.group(0)),
        start=match.start(),
        end=match.end(),
        kind=kind,
        volume=groups.get("volume") or "",
        reporter=_ws(groups.get("reporter") or ""),
        page=groups.get("page") or "",
        case_name=trim_case_name(_ws(groups.get("case") or "")),
        pincite=pincite,
        parenthetical=_ws(groups.get("paren") or ""),
        source_page=source_page(text, match.start()),
        source_line=source_line(text, match.start()),
    )


def flag_missing_pincite_comma(cite: Citation, match: re.Match[str]) -> None:
    if match.groupdict().get("badpincite"):
        add(
            cite.findings,
            "error",
            "missing_pincite_comma",
            "Pincite appears to be missing a comma before the page number.",
            f"{cite.volume} {cite.reporter} {cite.page}, {match.group('badpincite').strip()}".strip(),
        )


def extract_citations(text: str, cfg: MatterConfig | None = None) -> list[Citation]:
    citations: list[Citation] = []
    occupied: list[tuple[int, int]] = []
    for match in CASE_CITE_RE.finditer(text):
        cite = _citation_from_match(match, "case", text)
        style_audit(cite, cfg)
        flag_missing_pincite_comma(cite, match)
        citations.append(cite)
        occupied.append((match.start(), match.end()))
    for match in WL_LEXIS_RE.finditer(text):
        cite = Citation(
            text=match.group(0).strip(),
            start=match.start(),
            end=match.end(),
            kind="wl_lexis",
            reporter=match.group("service"),
            page=match.group("number"),
            pincite=(match.group("pincite") or "").strip(),
            parenthetical=(match.group("paren") or "").strip(),
            source_page=source_page(text, match.start()),
            source_line=source_line(text, match.start()),
        )
        style_audit(cite, cfg)
        citations.append(cite)
        occupied.append((match.start(), match.end()))
    for match in BARE_CITE_RE.finditer(text):
        if any(match.start() >= start and match.end() <= end for start, end in occupied):
            continue
        cite = _citation_from_match(match, "bare", text)
        style_audit(cite, cfg)
        flag_missing_pincite_comma(cite, match)
        citations.append(cite)
    return sorted(citations, key=lambda c: c.start)


def extract_short_references(text: str, citations: list[Citation]) -> list[ShortReference]:
    refs: list[ShortReference] = []
    cite_positions = sorted((cite.start, cite) for cite in citations)
    for pattern, kind in ((ID_RE, "id"), (SUPRA_RE, "supra")):
        for match in pattern.finditer(text):
            previous = [cite for start, cite in cite_positions if start < match.start()]
            target = previous[-1].text if previous else ""
            if kind == "id" and target:
                status = "resolved_context"
                message = "Id. appears to refer to the immediately preceding citation; confirm no intervening authority."
            elif kind == "id":
                status = "unresolved"
                message = "Id. has no preceding full citation in the extracted text."
            else:
                status = "not_resolved"
                message = "Supra short forms require manual source mapping to the full citation."
            refs.append(
                ShortReference(
                    text=match.group(0).strip(),
                    start=match.start(),
                    end=match.end(),
                    kind=kind,
                    source_page=source_page(text, match.start()),
                    source_line=source_line(text, match.start()),
                    status=status,
                    message=message,
                    target=target,
                )
            )
    return sorted(refs, key=lambda ref: ref.start)


def source_hint_for_authority(kind: str, match: re.Match[str]) -> tuple[str, str, str]:
    if kind == "usc":
        title = match.group("title")
        section = match.group("section").strip()
        normalized = f"{title} U.S.C. § {section}"
        url_section = re.sub(r"[^A-Za-z0-9]", "", section.split()[0])
        return (
            normalized,
            f"https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title{title}-section{url_section}",
            "Verify currency, effective date, amendments, and whether the title is positive law.",
        )
    if kind == "cfr":
        title = match.group("title")
        section = match.group("section").strip()
        normalized = f"{title} C.F.R. § {section}"
        return (
            normalized,
            f"https://www.ecfr.gov/current/title-{title}/section-{section}",
            "Verify current eCFR text, agency, effective date, and reserved/removed status.",
        )
    if kind == "federal_rule":
        rule_type = re.sub(r"\s+", " ", match.group("rule_type")).strip()
        rule = match.group("rule")
        return (
            f"Fed. R. {rule_type} {rule}",
            "https://www.uscourts.gov/forms-rules/current-rules-practice-procedure",
            "Verify the current federal rule and any applicable local rule or judge order.",
        )
    if kind == "state_statute":
        return (
            re.sub(r"\s+", " ", match.group(0)).strip(),
            "Use the official state code or legislature website for the selected jurisdiction.",
            "Verify official state code text, currency, and local citation format.",
        )
    if kind == "constitution":
        return (
            re.sub(r"\s+", " ", match.group(0)).strip(),
            "Use the official constitution source for the jurisdiction and any controlling annotations.",
            "Verify amendment/article text and controlling interpretive authority.",
        )
    return re.sub(r"\s+", " ", match.group(0)).strip(), "", "Verify against controlling source."


def extract_authorities(text: str) -> list[AuthorityMention]:
    patterns: list[tuple[str, re.Pattern[str]]] = [
        ("usc", USC_RE),
        ("cfr", CFR_RE),
        ("federal_rule", FED_RULE_RE),
        ("state_statute", STATE_STATUTE_RE),
        ("constitution", CONSTITUTION_RE),
    ]
    authorities: list[AuthorityMention] = []
    occupied: list[tuple[int, int]] = []
    for kind, pattern in patterns:
        for match in pattern.finditer(text):
            if any(match.start() >= start and match.end() <= end for start, end in occupied):
                continue
            normalized, source_hint, note = source_hint_for_authority(kind, match)
            authorities.append(
                AuthorityMention(
                    text=match.group(0).strip(),
                    start=match.start(),
                    end=match.end(),
                    kind=kind,
                    source_page=source_page(text, match.start()),
                    source_line=source_line(text, match.start()),
                    normalized=normalized,
                    source_hint=source_hint,
                    note=note,
                )
            )
            occupied.append((match.start(), match.end()))
    return sorted(authorities, key=lambda item: item.start)


def extract_doctrines(text: str, glossary: dict[str, Any]) -> list[DoctrineMention]:
    mentions: list[DoctrineMention] = []
    seen: set[tuple[str, int, int]] = set()
    for doctrine in glossary.get("doctrines") or []:
        for term in doctrine.get("terms") or []:
            pattern = re.compile(r"\b" + re.escape(str(term)) + r"\b", re.IGNORECASE)
            for match in pattern.finditer(text):
                key = (str(doctrine.get("id")), match.start(), match.end())
                if key in seen:
                    continue
                seen.add(key)
                mentions.append(
                    DoctrineMention(
                        doctrine_id=str(doctrine.get("id")),
                        term=match.group(0),
                        start=match.start(),
                        end=match.end(),
                        source_page=source_page(text, match.start()),
                        source_line=source_line(text, match.start()),
                        plain_language=str(doctrine.get("plain_language") or ""),
                        research_questions=[str(q) for q in doctrine.get("research_questions") or []],
                    )
                )
    for match in re.finditer(r"\bdoctrine of\s+([A-Za-z][A-Za-z \-]{2,60})", text, re.IGNORECASE):
        mentions.append(
            DoctrineMention(
                doctrine_id="unclassified-doctrine",
                term=match.group(0),
                start=match.start(),
                end=match.end(),
                source_page=source_page(text, match.start()),
                source_line=source_line(text, match.start()),
                plain_language="Named doctrine detected; load controlling authority before summarizing.",
                research_questions=["What jurisdiction controls?", "What are the elements?", "What authority defines the doctrine?"],
                status="needs_classification",
            )
        )
    return sorted(mentions, key=lambda item: item.start)


def extract_nearby_quotes(text: str, cite: Citation) -> list[dict[str, Any]]:
    lo = max(0, cite.start - QUOTE_WINDOW)
    hi = min(len(text), cite.end + QUOTE_WINDOW)
    found: list[dict[str, Any]] = []
    for match in QUOTE_RE.finditer(text[lo:hi]):
        quote = next(group for group in match.groups() if group)
        found.append(
            {
                "text": quote,
                "start": lo + match.start(),
                "end": lo + match.end(),
                "status": "not_checked",
                "message": "No authority text checked.",
            }
        )
    return found


def courtlistener_lookup(text: str, token: str | None) -> list[dict[str, Any]]:
    body = urllib.parse.urlencode({"text": text[:MAX_LOOKUP_CHARS]}).encode()
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if token:
        headers["Authorization"] = f"Token {token}"
    req = urllib.request.Request(COURTLISTENER_LOOKUP, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"CourtListener HTTP {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"CourtListener request failed: {exc}") from exc


def fetch_json(url: str, token: str | None) -> Any:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_authority_text(cl: dict[str, Any], token: str | None) -> str:
    chunks: list[str] = []
    for cluster in cl.get("clusters") or []:
        for opinion_url in cluster.get("sub_opinions") or []:
            try:
                opinion = fetch_json(opinion_url, token)
            except Exception:
                continue
            for field in ("html_with_citations", "plain_text", "html", "html_lawbox", "html_columbia"):
                value = opinion.get(field)
                if value:
                    chunks.append(strip_html(str(value)))
                    break
    return "\n".join(chunks)


def verify_quote(quote: str, source_text: str, min_quote_chars: int) -> tuple[str, str]:
    normalized_quote = normalize_quote(quote)
    if len(normalized_quote) < min_quote_chars:
        return "too_short", "Quote is too short for reliable normalized matching."
    if not source_text:
        return "not_checked", "No authority text available."
    return (
        ("verified", "Quote found in authority text.")
        if normalized_quote in normalize_quote(source_text)
        else ("not_found", "Quote was not found in available authority text.")
    )


def attach_courtlistener(citations: list[Citation], text: str, token: str | None) -> str:
    try:
        results = courtlistener_lookup(text, token)
    except RuntimeError as exc:
        return str(exc)
    by_span = {(item.get("start_index"), item.get("end_index")): item for item in results}
    by_cite: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        by_cite.setdefault(str(item.get("citation", "")).lower(), []).append(item)
    for cite in citations:
        match = by_span.get((cite.start, cite.end))
        if not match:
            match_list = by_cite.get(f"{cite.volume} {cite.reporter} {cite.page}".lower(), [])
            match = match_list[0] if match_list else None
        if match:
            cite.courtlistener = match
            status = match.get("status")
            if status == 200:
                pass
            elif status == 300:
                add(cite.findings, "warning", "cl_ambiguous", "CourtListener matched multiple authorities.")
            elif status == 404:
                add(cite.findings, "error", "cl_not_found", "CourtListener did not find this valid-looking citation.")
            elif status == 400:
                add(cite.findings, "error", "cl_bad_request", "CourtListener found an invalid or unknown reporter citation.")
            elif status == 429:
                add(cite.findings, "warning", "cl_throttled", "CourtListener lookup was throttled.")
    return ""


def attach_quote_review_findings(citations: list[Citation], cfg: MatterConfig) -> None:
    if not cfg.require_quote_pincites:
        return
    for cite in citations:
        if cite.nearby_quotes and cite.kind in {"case", "bare"} and not cite.pincite:
            add(
                cite.findings,
                "warning",
                "quote_without_pincite",
                "A nearby quotation is tied to this citation, but the citation has no pincite.",
            )


def serialize(cite: Citation) -> dict[str, Any]:
    return {
        "text": cite.text,
        "location": {
            "start": cite.start,
            "end": cite.end,
            "page": cite.source_page,
            "line": cite.source_line,
        },
        "kind": cite.kind,
        "case_name": cite.case_name,
        "volume": cite.volume,
        "reporter": cite.reporter,
        "page": cite.page,
        "pincite": cite.pincite,
        "parenthetical": cite.parenthetical,
        "findings": [finding.__dict__ for finding in cite.findings],
        "courtlistener": summarize_cl(cite.courtlistener),
        "nearby_quotes": cite.nearby_quotes,
    }


def serialize_short_reference(ref: ShortReference) -> dict[str, Any]:
    return {
        "text": ref.text,
        "kind": ref.kind,
        "location": {
            "start": ref.start,
            "end": ref.end,
            "page": ref.source_page,
            "line": ref.source_line,
        },
        "status": ref.status,
        "message": ref.message,
        "target": ref.target,
    }


def serialize_authority(item: AuthorityMention) -> dict[str, Any]:
    return {
        "text": item.text,
        "kind": item.kind,
        "location": {
            "start": item.start,
            "end": item.end,
            "page": item.source_page,
            "line": item.source_line,
        },
        "normalized": item.normalized,
        "source_hint": item.source_hint,
        "status": item.status,
        "note": item.note,
    }


def serialize_doctrine(item: DoctrineMention) -> dict[str, Any]:
    return {
        "doctrine_id": item.doctrine_id,
        "term": item.term,
        "location": {
            "start": item.start,
            "end": item.end,
            "page": item.source_page,
            "line": item.source_line,
        },
        "plain_language": item.plain_language,
        "research_questions": item.research_questions,
        "status": item.status,
    }


def summarize_cl(cl: dict[str, Any] | None) -> dict[str, Any] | None:
    if not cl:
        return None
    clusters = cl.get("clusters") or []
    return {
        "citation": cl.get("citation"),
        "normalized_citations": cl.get("normalized_citations"),
        "status": cl.get("status"),
        "error_message": cl.get("error_message"),
        "matches": [
            {
                "id": cluster.get("id"),
                "case_name": cluster.get("case_name") or cluster.get("case_name_full"),
                "absolute_url": cluster.get("absolute_url"),
                "date_filed": cluster.get("date_filed"),
                "citations": cluster.get("citations"),
            }
            for cluster in clusters[:5]
        ],
    }


def citation_label(cite: dict[str, Any]) -> str:
    cl = cite.get("courtlistener") or {}
    matches = cl.get("matches") or []
    if matches and matches[0].get("case_name"):
        return str(matches[0]["case_name"])
    return cite.get("case_name") or cite.get("text") or "Unknown authority"


def canonical_citation(cite: dict[str, Any]) -> str:
    cl = cite.get("courtlistener") or {}
    normalized = cl.get("normalized_citations") or []
    if normalized:
        return str(normalized[0])
    pieces = [cite.get("volume"), cite.get("reporter"), cite.get("page")]
    compact = " ".join(str(part) for part in pieces if part)
    return compact or cite.get("text") or ""


def table_of_authorities(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for cite in citations:
        key = citation_label(cite).lower() + "|" + canonical_citation(cite).lower()
        entry = grouped.setdefault(
            key,
            {
                "case_name": citation_label(cite),
                "citation": canonical_citation(cite),
                "count": 0,
                "locations": [],
                "first_text": cite.get("text"),
            },
        )
        entry["count"] += 1
        loc = cite.get("location") or {}
        entry["locations"].append(
            {
                "page": loc.get("page"),
                "line": loc.get("line"),
                "start": loc.get("start"),
            }
        )
    return sorted(grouped.values(), key=lambda item: item["case_name"].lower())


def review_summary(data: dict[str, Any]) -> dict[str, int]:
    counts = {
        "errors": 0,
        "warnings": 0,
        "quotes_not_found": 0,
        "quotes_not_checked": 0,
        "authorities": len(data.get("authorities") or []),
        "doctrines": len(data.get("doctrines") or []),
    }
    for cite in data["citations"]:
        for finding in cite["findings"]:
            if finding["severity"] == "error":
                counts["errors"] += 1
            elif finding["severity"] == "warning":
                counts["warnings"] += 1
        for quote in cite["nearby_quotes"]:
            if quote["status"] == "not_found":
                counts["quotes_not_found"] += 1
            elif quote["status"] == "not_checked":
                counts["quotes_not_checked"] += 1
    return counts


def markdown_report(data: dict[str, Any]) -> str:
    lines = [f"# DIFTCL Citation Audit", ""]
    if data.get("extraction_warning"):
        lines += [f"> NOTE: {data['extraction_warning']}", ""]
    config = data.get("matter_config") or {}
    if any(config.get(key) for key in ("filing_court", "jurisdiction", "document_type")):
        lines.append("## Matter Settings")
        if config.get("filing_court"):
            lines.append(f"- Filing court: {config['filing_court']}")
        if config.get("jurisdiction"):
            lines.append(f"- Jurisdiction: {config['jurisdiction']}")
        if config.get("document_type"):
            lines.append(f"- Document type: {config['document_type']}")
        if config.get("local_rules_enabled"):
            target = config.get("local_rules_url") or config.get("local_rules_court_id") or "not configured"
            lines.append(f"- Local rules: enabled; target {target}")
        lines.append("")
    if data.get("courtlistener_error"):
        lines += [f"CourtListener: {data['courtlistener_error']}", ""]
    summary = review_summary(data)
    lines += [
        "## Review Summary",
        f"- Citations found: {len(data['citations'])}",
        f"- Errors: {summary['errors']}",
        f"- Warnings: {summary['warnings']}",
        f"- Quotes not found: {summary['quotes_not_found']}",
        f"- Quotes not checked: {summary['quotes_not_checked']}",
        f"- Short-form references: {len(data.get('short_references') or [])}",
        f"- Statutes/rules/regulations: {summary['authorities']}",
        f"- Doctrines/standards: {summary['doctrines']}",
        "",
    ]
    for idx, cite in enumerate(data["citations"], 1):
        cl = cite.get("courtlistener") or {}
        status = cl.get("status", "not_checked")
        lines.append(f"## {idx}. `{cite['text']}`")
        lines.append(
            f"- Location: page {cite['location']['page']}, line {cite['location']['line']} "
            f"(chars {cite['location']['start']}-{cite['location']['end']})"
        )
        lines.append(f"- CourtListener: {status}")
        if cl.get("normalized_citations"):
            lines.append(f"- Normalized: {', '.join(cl['normalized_citations'])}")
        matches = cl.get("matches") or []
        if matches:
            lines.append(f"- Match: {matches[0].get('case_name')} ({matches[0].get('date_filed')})")
        if cite["findings"]:
            for finding in cite["findings"]:
                suggestion = f" Suggested: `{finding['suggestion']}`" if finding.get("suggestion") else ""
                lines.append(f"- {finding['severity'].upper()} {finding['code']}: {finding['message']}{suggestion}")
        else:
            lines.append("- Style findings: none")
        if cite["nearby_quotes"]:
            for quote in cite["nearby_quotes"]:
                lines.append(f"- Quote {quote['status']}: \"{quote['text'][:120]}\" - {quote['message']}")
        lines.append("")
    short_refs = data.get("short_references") or []
    if short_refs:
        lines += ["## Short-Form References", ""]
        for ref in short_refs:
            target = f" Target: `{ref['target']}`" if ref.get("target") else ""
            lines.append(
                f"- {ref['status']}: `{ref['text']}` at page {ref['location']['page']}, "
                f"line {ref['location']['line']}. {ref['message']}{target}"
            )
        lines.append("")
    if data.get("table_of_authorities"):
        lines += ["## Table Of Authorities Draft", ""]
        for entry in data["table_of_authorities"]:
            locs = ", ".join(
                f"p. {loc['page']} l. {loc['line']}" for loc in entry["locations"][:12]
            )
            lines.append(
                f"- {entry['case_name']}, {entry['citation']} - {entry['count']} mention(s): {locs}"
            )
        lines.append("")
    if data.get("authorities"):
        lines += ["## Statutes, Rules, Regulations, And Constitutional Provisions", ""]
        for item in data["authorities"]:
            lines.append(
                f"- `{item['text']}` ({item['kind']}) at page {item['location']['page']}, "
                f"line {item['location']['line']}: {item['normalized']}"
            )
            if item.get("source_hint"):
                lines.append(f"  Source hint: {item['source_hint']}")
        lines.append("")
    if data.get("doctrines"):
        lines += ["## Doctrines And Standards", ""]
        for item in data["doctrines"]:
            lines.append(
                f"- `{item['term']}` at page {item['location']['page']}, line {item['location']['line']}: "
                f"{item.get('plain_language') or 'Issue spotted; verify controlling law.'}"
            )
        lines.append("")
    return "\n".join(lines)


def _dedupe_authorities(authorities: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in authorities:
        key = (item.get("normalized") or item.get("text") or "").lower()
        entry = grouped.get(key)
        if entry is None:
            grouped[key] = {**item, "count": 1}
        else:
            entry["count"] += 1
    return sorted(grouped.items(), key=lambda kv: kv[1]["text"].lower())


def _dedupe_doctrines(doctrines: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in doctrines:
        key = item.get("doctrine_id") or (item.get("term") or "").lower()
        entry = grouped.get(key)
        if entry is None:
            grouped[key] = {**item, "count": 1}
        else:
            entry["count"] += 1
    return sorted(grouped.items(), key=lambda kv: kv[1]["term"].lower())


def review_report(data: dict[str, Any]) -> str:
    lines = ["# DIFTCL Attorney/Paralegal Review Packet", ""]
    if data.get("extraction_warning"):
        lines += [f"> NOTE: {data['extraction_warning']}", ""]
    summary = review_summary(data)
    lines += [
        "## Triage",
        f"- Correct citation-form errors: {summary['errors']}",
        f"- Review style warnings: {summary['warnings']}",
        f"- Resolve unsupported quotes: {summary['quotes_not_found']}",
        f"- Supply authority text for unchecked quotes: {summary['quotes_not_checked']}",
        f"- Resolve short-form references: {len(data.get('short_references') or [])}",
        f"- Verify statutes/rules/regulations: {summary['authorities']}",
        f"- Research doctrines/standards: {summary['doctrines']}",
        "",
        "## Action Items",
    ]
    if not data["citations"]:
        lines.append("- No case citations were extracted. Confirm the document text was readable.")
    action_count = 0
    for cite in data["citations"]:
        problems = cite["findings"] or []
        unsupported = [q for q in cite["nearby_quotes"] if q["status"] in {"not_found", "not_checked", "too_short"}]
        if not problems and not unsupported:
            continue
        action_count += 1
        lines.append(f"- `{cite['text']}` at page {cite['location']['page']}, line {cite['location']['line']}")
        for finding in problems:
            suggestion = f" Suggested: `{finding['suggestion']}`" if finding.get("suggestion") else ""
            lines.append(f"  - {finding['severity'].upper()} {finding['code']}: {finding['message']}{suggestion}")
        for quote in unsupported:
            lines.append(f"  - QUOTE {quote['status']}: \"{quote['text'][:120]}\" - {quote['message']}")
    if data["citations"] and action_count == 0:
        lines.append("- No citation-form or quote-support action items found in this pass.")
    config = data.get("matter_config") or {}
    if config.get("local_rules_enabled") and not (config.get("local_rules_url") or config.get("local_rules_court_id")):
        lines.append("- LOCAL RULES: enabled but no court ID or rules URL is configured.")
    elif config.get("local_rules_enabled"):
        target = config.get("local_rules_url") or config.get("local_rules_court_id")
        lines.append(f"- LOCAL RULES: configured target `{target}`; verify fetched rule text before filing.")
    for norm, item in _dedupe_authorities(data.get("authorities") or []):
        count = item["count"]
        times = f" ({count}×)" if count > 1 else ""
        lines.append(f"- AUTHORITY: verify `{item['text']}`{times} against {item.get('source_hint') or 'the controlling source'}.")
    for doc_id, item in _dedupe_doctrines(data.get("doctrines") or []):
        count = item["count"]
        times = f" ({count}×)" if count > 1 else ""
        lines.append(f"- DOCTRINE: research `{item['term']}`{times} elements and controlling authority.")
    short_refs = data.get("short_references") or []
    if short_refs:
        lines += ["", "## Short Forms To Resolve"]
        for ref in short_refs:
            lines.append(
                f"- `{ref['text']}` at page {ref['location']['page']}, line {ref['location']['line']}: {ref['message']}"
            )
    return "\n".join(lines)


def strategy_report(data: dict[str, Any], cfg: MatterConfig) -> str:
    summary = review_summary(data)
    citations = data.get("citations") or []
    short_refs = data.get("short_references") or []
    lines = ["# DIFTCL Strategy / Tactics / Contrarian Review", ""]
    lines += [
        "This is issue spotting and litigation-preparation support, not legal advice.",
        "",
        "## Assumptions",
        f"- Position lens: {cfg.strategy_position}",
        f"- Objective: {cfg.strategy_objective or 'not specified'}",
        f"- Citations reviewed: {len(citations)}",
        f"- Citation errors: {summary['errors']}",
        f"- Citation warnings: {summary['warnings']}",
        f"- Short-form references: {len(short_refs)}",
        "",
        "## Strategy",
    ]
    if not citations:
        lines.append("- No extracted authorities yet; first strategic task is source collection and citation extraction.")
    else:
        clean = [cite for cite in citations if not cite.get("findings")]
        risky = [cite for cite in citations if cite.get("findings")]
        if clean:
            lines.append(f"- Build around {len(clean)} citation(s) with no mechanical style findings in this pass.")
        if risky:
            lines.append(f"- Do not lean on {len(risky)} citation(s) with unresolved findings until corrected or verified.")
        unchecked_quotes = sum(1 for cite in citations for quote in cite.get("nearby_quotes", []) if quote.get("status") == "not_checked")
        not_found_quotes = sum(1 for cite in citations for quote in cite.get("nearby_quotes", []) if quote.get("status") == "not_found")
        if not_found_quotes:
            lines.append("- Unsupported quoted language is a strategic risk; replace, paraphrase without quotes, or verify from the authority.")
        if unchecked_quotes:
            lines.append("- Quoted language remains unchecked; collect opinion text before treating the quote as usable.")
    config = data.get("matter_config") or {}
    if config.get("local_rules_enabled"):
        target = config.get("local_rules_url") or config.get("local_rules_court_id") or "not configured"
        lines.append(f"- Local-rule review is in scope for `{target}`; confirm citation, filing, and judge-specific requirements.")
    else:
        lines.append("- Local-rule review is not enabled; do not assume filing-court compliance.")
    lines += ["", "## Tactics"]
    if summary["errors"]:
        lines.append("- Fix `error` findings before investing in argument polishing.")
    if summary["warnings"]:
        lines.append("- Clear style warnings, especially reporter normalization, missing pincites, and parenthetical issues.")
    if short_refs:
        lines.append("- Resolve `Id.`, `supra`, and abbreviated references against full citations before filing.")
    lines.append("- Generate a TOA draft after citation cleanup and compare mention counts after edits.")
    lines.append("- Run quote verification with source text or CourtListener opinion text for every quotation.")
    lines += ["", "## Contrarian Review"]
    if citations:
        lines.append("- Opposing counsel may attack any citation that lacks a pincite for a quoted or specific proposition.")
        lines.append("- The court may discount authorities that are ambiguous, unpublished, nonprecedential, stale, or unmatched.")
    if summary["quotes_not_found"]:
        lines.append("- A direct quote not found in source text is an impeachment point; treat it as urgent.")
    if summary["quotes_not_checked"]:
        lines.append("- Unchecked quotes invite challenge because citation validity does not prove quote accuracy.")
    if short_refs:
        lines.append("- Short forms can be attacked if the referent is unclear or an intervening authority breaks the chain.")
    if data.get("authorities"):
        lines.append("- Statutes and rules can be attacked if the cited version, effective date, or subsection is wrong.")
    if data.get("doctrines"):
        lines.append("- Named doctrines need element-by-element support; a label alone is not proof.")
    lines.append("- Ask what adverse authority, procedural bar, waiver, or standard-of-review issue is missing from the draft.")
    return "\n".join(lines)


def authority_report(data: dict[str, Any]) -> str:
    lines = ["# DIFTCL Doctrine / Statute Extraction", ""]
    authorities = data.get("authorities") or []
    doctrines = data.get("doctrines") or []
    lines += [
        f"- Statutes/rules/regulations found: {len(authorities)}",
        f"- Doctrines/standards found: {len(doctrines)}",
        "",
    ]
    if authorities:
        lines += ["## Authorities", ""]
        for item in authorities:
            lines.append(f"- `{item['text']}` ({item['kind']})")
            lines.append(f"  - Location: page {item['location']['page']}, line {item['location']['line']}")
            if item.get("normalized"):
                lines.append(f"  - Normalized: {item['normalized']}")
            if item.get("source_hint"):
                lines.append(f"  - Source hint: {item['source_hint']}")
            lines.append(f"  - Check: {item.get('note') or 'Verify against controlling source.'}")
    if doctrines:
        lines += ["", "## Doctrines / Standards", ""]
        for item in doctrines:
            lines.append(f"- `{item['term']}`")
            lines.append(f"  - Location: page {item['location']['page']}, line {item['location']['line']}")
            if item.get("plain_language"):
                lines.append(f"  - Education note: {item['plain_language']}")
            for question in item.get("research_questions") or []:
                lines.append(f"  - Research: {question}")
    return "\n".join(lines)


def education_report(data: dict[str, Any]) -> str:
    lines = [authority_report(data), "", "## Education Boundaries", ""]
    lines.append("- These notes are legal research support and plain-language orientation, not legal advice.")
    lines.append("- Verify statutes and rules against official current sources before relying on them.")
    lines.append("- Verify doctrine elements against controlling jurisdiction and procedural posture.")
    return "\n".join(lines)


def toa_report(data: dict[str, Any]) -> str:
    lines = ["# Draft Table Of Authorities", ""]
    entries = data.get("table_of_authorities") or []
    if not entries:
        return "# Draft Table Of Authorities\n\nNo case authorities extracted.\n"
    for entry in entries:
        locs = ", ".join(f"{loc['page']}:{loc['line']}" for loc in entry["locations"])
        lines.append(f"- {entry['case_name']}, {entry['citation']} ({entry['count']}): {locs}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Matter config file, default diftcl.yaml when present")
    parser.add_argument("--input", help="Input TXT/MD/HTML/PDF/DOCX file")
    parser.add_argument("--text", help="Inline text to audit")
    parser.add_argument("--cite", help="Single citation to audit")
    parser.add_argument(
        "--courtlistener",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Validate citations with CourtListener",
    )
    parser.add_argument(
        "--verify-quotes",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Verify nearby quotes against available authority text",
    )
    parser.add_argument("--source", help="Authority/source text file to use for quote checks")
    parser.add_argument("--filing-court", help="Target filing court for local-rule-sensitive review")
    parser.add_argument("--jurisdiction", help="Jurisdiction for matter-specific citation checks")
    parser.add_argument("--document-type", help="Document type, such as brief, memo, motion, or notice")
    parser.add_argument("--quote-min-chars", type=int, help="Minimum normalized quote length for matching")
    parser.add_argument("--strict", action=argparse.BooleanOptionalAction, default=None, help="Enable stricter review")
    parser.add_argument(
        "--local-rules-enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Record that local-rule review is enabled for this matter",
    )
    parser.add_argument("--local-rules-court-id", help="Court/source ID selected from the bundled rule source registry")
    parser.add_argument("--local-rules-url", help="Explicit official local rules URL selected by the user")
    parser.add_argument(
        "--list-rule-sources",
        action="store_true",
        help="List bundled federal/state court rule source directories without fetching them",
    )
    parser.add_argument("--rule-source-query", help="Filter bundled court rule sources by ID, name, or URL")
    parser.add_argument("--calendar-from", help="Trigger date for deadline calculation, YYYY-MM-DD")
    parser.add_argument("--calendar-rule", help="Rule ID from --calendar-rules-file")
    parser.add_argument("--calendar-rules-file", help="Matter-specific JSON rules file for deadline calculations")
    parser.add_argument("--calendar-days", type=int, help="Ad hoc number of days when no calendar rule is selected")
    parser.add_argument("--calendar-count", choices=("calendar", "business"), default="calendar")
    parser.add_argument("--calendar-direction", choices=("after", "before"), default="after")
    parser.add_argument("--calendar-roll", choices=("next_business", "previous_business", "none"), default="next_business")
    parser.add_argument("--calendar-include-trigger-day", action="store_true")
    parser.add_argument("--calendar-holidays", help="Comma-separated YYYY-MM-DD holidays for deadline calculation")
    parser.add_argument("--strategy", action="store_true", help="Emit strategy/tactics/contrarian issue-spotting output")
    parser.add_argument("--strategy-position", choices=("neutral", "plaintiff", "defense", "movant", "opponent"), help="Strategy lens")
    parser.add_argument("--strategy-objective", help="User-defined litigation objective for strategy review")
    parser.add_argument("--authorities", action="store_true", help="Emit statute/rule/regulation/doctrine extraction output")
    parser.add_argument("--educate", action="store_true", help="Emit plain-language education notes for extracted authorities and doctrines")
    parser.add_argument("--doctrine-glossary", help="Custom doctrine glossary JSON file")
    parser.add_argument(
        "--output-format",
        choices=("markdown", "json", "review", "toa", "calendar", "strategy", "authorities", "education"),
        help="Output format",
    )
    parser.add_argument("--toa", action="store_true", help="Emit a draft table of authorities")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    args = parser.parse_args()
    if args.list_rule_sources:
        registry = filter_rule_sources(load_rule_source_registry(), args.rule_source_query or "")
        if args.json:
            print(json.dumps(registry, indent=2, sort_keys=True))
        else:
            print(format_rule_sources(registry))
        return 0

    cfg = build_config(args)
    if args.calendar_from and not (args.input or args.text or args.cite):
        result = calendar_from_args(args, cfg)
        if cfg.output_format == "json":
            print(json.dumps({"calendar": result}, indent=2, sort_keys=True))
        else:
            print(calendar_report(result))
        return 0

    try:
        text = read_input(args)
    except ExtractionError as exc:
        print(f"diftcl: {exc}", file=sys.stderr)
        return 1
    extraction_warning = ""
    if args.input and not text.strip():
        extraction_warning = (
            f"No extractable text from {Path(args.input).name}. The document may be a "
            "scanned image with no text layer (OCR required) or otherwise empty."
        )
    citations = extract_citations(text, cfg)
    for cite in citations:
        cite.nearby_quotes = extract_nearby_quotes(text, cite)
    attach_quote_review_findings(citations, cfg)
    short_references = extract_short_references(text, citations)
    authorities = extract_authorities(text)
    doctrines = extract_doctrines(text, load_doctrine_glossary(args.doctrine_glossary or cfg.doctrine_glossary_file))

    token = os.environ.get("COURTLISTENER_TOKEN")
    cl_error = ""
    if cfg.courtlistener and citations:
        cl_error = attach_courtlistener(citations, text, token)

    source_text = ""
    if args.source:
        source_text = read_path_text(args.source)

    if cfg.verify_quotes:
        for cite in citations:
            authority_text = source_text
            if not authority_text and cite.courtlistener and cite.courtlistener.get("status") == 200:
                authority_text = fetch_authority_text(cite.courtlistener, token)
            for quote in cite.nearby_quotes:
                status, message = verify_quote(quote["text"], authority_text, cfg.quote_min_chars)
                quote["status"] = status
                quote["message"] = message

    data = {
        "citations": [serialize(cite) for cite in citations],
        "short_references": [serialize_short_reference(ref) for ref in short_references],
        "authorities": [serialize_authority(item) for item in authorities],
        "doctrines": [serialize_doctrine(item) for item in doctrines],
        "courtlistener_error": cl_error,
        "extraction_warning": extraction_warning,
        "matter_config": {
            "filing_court": cfg.filing_court,
            "jurisdiction": cfg.jurisdiction,
            "document_type": cfg.document_type,
            "strict": cfg.strict,
            "courtlistener": cfg.courtlistener,
            "verify_quotes": cfg.verify_quotes,
            "quote_min_chars": cfg.quote_min_chars,
            "require_quote_pincites": cfg.require_quote_pincites,
            "require_parenthetical_court": cfg.require_parenthetical_court,
            "local_rules_enabled": cfg.local_rules_enabled,
            "local_rules_court_id": cfg.local_rules_court_id,
            "local_rules_url": cfg.local_rules_url,
            "local_rules_cache_ttl_days": cfg.local_rules_cache_ttl_days,
            "local_rules_max_requests": cfg.local_rules_max_requests,
            "local_rules_retry_limit": cfg.local_rules_retry_limit,
            "local_rules_min_delay_seconds": cfg.local_rules_min_delay_seconds,
            "calendar_enabled": cfg.calendar_enabled,
            "calendar_rules_file": cfg.calendar_rules_file,
            "strategy_enabled": cfg.strategy_enabled,
            "strategy_position": cfg.strategy_position,
            "strategy_objective": cfg.strategy_objective,
            "doctrine_education_enabled": cfg.doctrine_education_enabled,
            "doctrine_glossary_file": cfg.doctrine_glossary_file,
            "output_format": cfg.output_format,
        },
    }
    if args.calendar_from:
        data["calendar"] = calendar_from_args(args, cfg)
    data["table_of_authorities"] = table_of_authorities(data["citations"])
    if cfg.output_format == "json":
        print(json.dumps(data, indent=2, sort_keys=True))
    elif cfg.output_format == "calendar" and data.get("calendar"):
        print(calendar_report(data["calendar"]))
    elif cfg.output_format == "strategy":
        print(strategy_report(data, cfg))
    elif cfg.output_format == "authorities":
        print(authority_report(data))
    elif cfg.output_format == "education":
        print(education_report(data))
    elif cfg.output_format == "review":
        print(review_report(data))
    elif cfg.output_format == "toa":
        print(toa_report(data))
    else:
        print(markdown_report(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
