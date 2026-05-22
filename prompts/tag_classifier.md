You are classifying vehicle regulations against a controlled taxonomy.
You will NOT summarize, rewrite, or interpret the regulation. You will ONLY
select tag values from the lists below.

RULES:
- Select ONLY values that appear verbatim in the controlled vocabulary.
- If a facet does not clearly apply, return an empty array — do not guess.
- Apply tags consistently across regions: identical subject matter must
  receive identical tags regardless of where the regulation originates.
- If the regulation references a UN R number (e.g., UN R48), treat it as
  equivalent to the corresponding regional regulation for tagging purposes.

INPUT FORMAT (one JSON record per line in batch_NNN.jsonl):
  {"id":"...","region":"...","citation":"...","title":"...","body":"..."}

OUTPUT FORMAT (one JSON record per line in batch_NNN_results.jsonl):
  {"id":"<same id>","commodities":[...],"systems":[...],"vehicle_categories":[...],"rationale_short":"<one sentence>"}
  No prose before or after the JSON. One line per input record.

FEW-SHOT EXAMPLES (to anchor consistency):

  Input  — id: us-fmvss-108, 49 CFR §571.108, "Lamps, reflective devices, and associated equipment"
  Output — {"id":"us-fmvss-108","commodities":["Lighting modules","Wiring"],"systems":["Lighting & signaling"],"vehicle_categories":["Passenger car","Light truck","Heavy truck","Bus","Motorcycle"],"rationale_short":"Lighting equipment regulation across all motor vehicle categories."}

  Input  — id: us-fmvss-208, 49 CFR §571.208, "Occupant crash protection"
  Output — {"id":"us-fmvss-208","commodities":["Airbags","Seatbelts","Seats"],"systems":["Crashworthiness","Restraints"],"vehicle_categories":["Passenger car","Light truck"],"rationale_short":"Frontal-impact occupant protection requirements."}

  Input  — id: us-fmvss-301, 49 CFR §571.301, "Fuel system integrity"
  Output — {"id":"us-fmvss-301","commodities":["Fuel tanks","Hoses & lines"],"systems":["Fuel safety","Crashworthiness"],"vehicle_categories":["Passenger car","Light truck","Heavy truck","Bus"],"rationale_short":"Post-crash fuel leakage limits."}

INSTRUCTIONS FOR CLASSIFYING A BATCH:

1. Read tagging_batches/_vocab.md for the current controlled vocabulary (it is auto-generated from taxonomy.yaml and includes the lists below).
2. For each line in batch_NNN.jsonl, produce one output JSON line.
3. Save all output lines to batch_NNN_results.jsonl (same directory, same batch number).
4. Repeat for each remaining batch file before running tag_import.py.
