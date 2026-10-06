# Patch-writer brief — turn review findings into exact record patches

You convert reviewer findings into **exact, machine-applicable field values** for records in
`regulations/<id>.md`. You do NOT edit those files. You write one JSON file:
`review/patches/<GROUP>.json`.

## Inputs
- `review/patches/<GROUP>.input.json` — the medium/high findings for your records (from the swarm).
- `regulations/<id>.md` — the record (YAML frontmatter + body). Re-read it before every patch.
- `taxonomy.yaml` — the ONLY allowed values for `systems`, `commodities`, `vehicle_categories`,
  `status`.

## Rules
1. Only patch a field when the finding is right AND you can state the exact correct value. The
   finding may itself be wrong; re-check it against the record body and your knowledge. If in
   doubt, skip it and say why — a skipped fix is better than a new error.
2. Allowed fields and formats:
   - `title` (string — include the instrument's subject, e.g. "MVSR s. 208 — Occupant Protection")
   - `summary` (string, 1–3 factual sentences about THIS instrument; no requirements you cannot
     support; no "..." truncation)
   - `status` — one of: in-force, upcoming, proposed, withdrawn, superseded
   - `status_note` (short string, e.g. "Applies only to vehicles manufactured before 1 Sep 2009; superseded by FMVSS 202a.")
   - `systems`, `commodities`, `vehicle_categories` — FULL replacement lists using exact taxonomy values
   - `un_equivalent`, `un_equivalent_ai` — FULL replacement lists, each item exactly `UN R<number>`
     optionally followed by one capital letter (e.g. `UN R13H`). Use [] for "no UN counterpart".
     `un_equivalent_ai` = plausible counterpart; `un_equivalent` = only when the record body or
     official title itself states the UN Regulation is adopted/equivalent.
   - `effective_date` (YYYY-MM-DD; the date the instrument applies/entered into force, not adoption)
   - `citation` (string)
   - `_stub_body: true` — when the BODY describes a different instrument/topic (copied template).
     The body will be replaced by an honest "reference stub" notice; also supply a correct `summary`.
3. Do not patch `body` text otherwise, ids, source_url, or anything not listed.
4. Ignore findings about "no regulation text" in the body (handled separately in the UI).

## Output — `review/patches/<GROUP>.json`
```json
{
  "group": "<GROUP>",
  "patches": { "<record id>": { "<field>": <value>, "_why": "one line: which finding / evidence" } },
  "skipped": [ { "id": "...", "field": "...", "reason": "..." } ]
}
```
Validate with `python -m json.tool`. Final message: one paragraph — records patched, fields
patched, findings skipped, anything you think the orchestrator must double-check.
