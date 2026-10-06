# Low-severity patch brief

You are turning **low-severity** reviewer findings into exact record patches. Follow
`review/PATCH_BRIEF.md` (same output format, allowed fields and taxonomy rules) with these changes.

## What is different for low severity
1. **Records changed after the review.** Many records have been corrected since the findings
   were written. 183 bodies were also re-pulled as official full text and their metadata was
   re-checked. Re-read the CURRENT record (front matter and body) before acting on any finding. If the
   finding no longer applies, skip it with the reason "already fixed".
2. **Higher bar.** Patch only when the current record or its body clearly supports the change, or
   you are certain from well-established knowledge. A finding marked `unverifiable` or
   `confidence: low` needs evidence in the body. If you can't find it there, skip.
3. **`source_url` is allowed.** You have internet access. Before proposing a new URL, check it with
   `curl -sIL -m 20 -A "Mozilla/5.0" <url>`. It must return 200, and it must point to the official
   source for THIS instrument. Keep the current URL if it already works and is official.
4. **No new summaries for style alone.** Rewrite a summary only if it is wrong or cut off ("...").
   The rule for `_stub_body` is the same as in PATCH_BRIEF.
5. **Write the output to `review/low/<GROUP>.json`**, not `review/patches/`.

Inputs are in `review/low/<GROUP>.input.json`. Check the output with `python -m json.tool`. Your
final message should be one paragraph: the counts of patched, skipped and already-fixed findings,
plus anything the orchestrator should double-check.
