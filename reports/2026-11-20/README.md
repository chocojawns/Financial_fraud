# Discovery run — November 20, 2026

**Status: blocked before filing collection. This is a run-status report, not a completed fraud analysis.**

## Research question

Which S&P 500 financial companies separately disclose fraud-related financial
amounts, what do those amounts represent, and where are they reported?

## Current project state

`discovery.py` searches primary documents and HTML/text exhibits. Financial mode
looks for explicit fraud indicators and monetary expressions in the same sentence,
retains source quotations, and separates amount tags from broader passage tags.
Categories are suggestions requiring review; numbers are not automatically summed.

Pilot and CIK-file batch modes are implemented. The default SEC contact is
andy@andyj.tech. Windows and Debian instructions are in the repository README.
All 26 automated tests passed on this date. Their SEC/OpenAI calls are mocked;
those results do not establish live data coverage.

## Attempted scope

| Company | CIK | Metadata result | Filing coverage |
|---|---|---|---|
| JPMorgan Chase | 19617 | Proxy CONNECT returned 403 Forbidden | Not collected |
| Bank of America | 70858 | Proxy CONNECT returned 403 Forbidden | Not collected |

This is the agreed two-company starting sample, not the full S&P 500 Financials
universe. No `--pilot` cap was used: the intended run covered all available annual,
quarterly, and current reports (including amendments) for these two CIKs within
2020–2026 filing dates. No filings dated after the run date can have been observed.

Command, run from the repository root:

```bash
python3 discovery.py --cik-file examples/pilot_ciks.txt --forms 10-K 10-K/A 10-Q 10-Q/A 8-K 8-K/A --output reports/2026-11-20/discovery.jsonl
```

On Windows replace `python3` with `python`.

## Observed outcome

- Process exit code: **1 (failure)**.
- Company metadata requests attempted: **2**.
- Successful company metadata requests: **0**.
- Filing documents searched: **0**.
- Fraud disclosure findings: **unavailable**.
- Fraud-related financial amounts: **unavailable**, not zero.
- OpenAI analysis: **not run**; no model calls or paid analysis.

The empty amounts CSV contains only its header because collection failed. It must
not be interpreted as evidence that either company had no fraud losses or did not
disclose fraud amounts. No company comparison or industry inference is possible.

## Files

- `discovery.jsonl`: actual error records from the command.
- `discovery_coverage.csv`: two incomplete metadata records.
- `discovery_amounts.csv`: header only; no financial evidence was collected.
- `discovery.csv`: broad error/coverage export.
- `run_manifest.json`: command, source revision, outcome, and output checksums.

## Blocker and continuation

The running cloud network policy is restricted and currently has no custom SEC
host grants. The saved environment draft already contains `data.sec.gov`,
`www.sec.gov`, and `api.openai.com`, but these entries are not applied to this
running instance. No duplicate draft changes were made for this run.

Review and save/apply that existing draft in environment settings. SEC collection
requires the first two domains; OpenAI access and credentials are optional and
are not needed for the first discovery run. After applying, check current runtime
status and make a fresh SEC request before rerunning collection.

Preserve this failed attempt as an audit record. Save the next run to a new output
folder. Review the two-company findings before expanding to a verified, dated
S&P 500 Financials CIK list. Deduplicate repeated events/amounts across filings,
confirm company attribution, accounting category, currency, and reporting period,
and keep no-disclosure findings separate from incomplete scans.
