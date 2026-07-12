# Litigation Calendar And Strategy Review

Use this reference when the user asks for deadline calculations, litigation timelines, strategy, tactics, or contrarian review.

## Deadline And Calendar Rules

Deadline calculations are high-risk. Do not invent jurisdiction rules. Use one of:

- a user-supplied scheduling order;
- a user-supplied rule text excerpt;
- a configured `calendar_rules_file`;
- an official local-rule/statute source fetched under `references/local-rule-sources.md` safety limits.

If no controlling rule source is available, provide only a generic calculation and mark it `not_authoritative`.

Always report:

- trigger event and trigger date;
- rule ID or source authority;
- number of days;
- calendar-day or business-day counting method;
- whether the trigger day is included;
- weekend/holiday roll rule;
- holidays used;
- calculated deadline;
- explicit attorney-review warning.

Do not calculate deadlines from memory when the jurisdiction, rule source, or triggering event is unclear.

## Calendar Rule File

Start from `templates/calendar-rules.json`.

Required fields for each rule:

```json
{
  "id": "opposition-after-motion-service",
  "label": "Opposition deadline after motion service",
  "trigger": "service",
  "days": 14,
  "count": "calendar",
  "direction": "after",
  "roll": "next_business",
  "include_trigger_day": false,
  "authority": "Local Rule ...",
  "notes": "Confirm method of service and judge-specific order."
}
```

Use `business` counting only when the controlling rule says so. Otherwise, many litigation rules count calendar days and then roll if the deadline lands on a weekend or legal holiday.

## Strategy, Tactics, Contrarian Review

This mode is for issue spotting and preparation, not legal advice.

Use three separate lenses:

- **Strategy**: objectives, strongest authorities, weakest authorities, dispositive risks, preservation issues.
- **Tactics**: cite fixes, quote fixes, TOA cleanup, local-rule tasks, deadline checks, source collection.
- **Contrarian**: what opposing counsel or the court may attack, missing authority, overclaimed quotes, ambiguity, adverse procedural posture.

Ground every point in:

- extracted citations;
- quote verification status;
- local-rule or calendar configuration gaps;
- user-provided facts;
- explicit assumptions.

Do not fabricate case holdings, procedural rules, deadlines, or strategic facts. When a needed fact is absent, make it an action item.
