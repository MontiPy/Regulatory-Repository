# Verifier brief: check record metadata against freshly pulled regulation text

These records now hold the **official regulation text**, from the 2026-10 re-pull. Their summaries
and tags were written earlier, often from a generic template, so they may not match the text.
Check each record against its own body. Then write `review/verify/<GROUP>.json`.

## Inputs
- `review/verify/<GROUP>.input.json`: the list of record ids.
- `regulations/<id>.md`: YAML front matter plus the body. Bodies can be several MB. Read the front
  matter, then the parts of the body that settle the facts. Use the title and scope or
  application clause, the definitions of the vehicle categories covered, and the dates
  (compilation date, entry into force, transitional provisions). Use Grep to find clauses such
  as "Scope", "Application", "applies to", "category M1" and "UN Regulation No".
- `taxonomy.yaml`: the only allowed values for `systems`, `commodities`, `vehicle_categories` and
  `status`.

## For every record, decide
1. **summary**: Is it accurate for THIS text? If yes, set `"_confirmed": true`. If not, write a new
   factual summary of 1–3 sentences, at most 600 characters. Say what the instrument regulates
   and its scope. Only state what the text supports, and never end with "...".
2. **title**: change it only if it names the wrong instrument or subject.
3. **systems / commodities / vehicle_categories**: patch them only when they are clearly wrong for
   the text. A patch is a full replacement list using exact taxonomy values.
4. **un_equivalent**: list only UN Regulations that the text itself says it adopts or treats as
   equivalent. **un_equivalent_ai**: plausible counterparts. Use the format `UN R<number>`,
   optionally followed by one capital letter.
5. **effective_date / status / status_note**: patch them only when the text clearly contradicts
   them. Today is 2026-10-06.

Every record must get either `_confirmed: true` or a new `summary`. Leave out fields that are
already right.

## Output: `review/verify/<GROUP>.json`
```json
{ "group": "<GROUP>",
  "patches": { "<id>": { "_confirmed": true, "<field>": <value>, "_why": "one line: what in the text shows this" } },
  "skipped": [ { "id": "...", "reason": "..." } ] }
```
Do not edit any other file. Check the output with `python -m json.tool`. Your final message
should be one paragraph: how many records you confirmed, how many you changed, and anything
the orchestrator should double-check.
