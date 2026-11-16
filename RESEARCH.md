# Research notes

## Agreed project scope

- Goal: identify separately disclosed fraud-related financial amounts, their
  meaning, and accounting location among S&P 500 Financials.
- Filing-date window: 2020–2026, with 2026 incomplete until year-end.
- Early collection covered all financial SIC filers; the current request starts
  with any user-supplied CIK. SIC membership is not S&P 500/GICS membership.
- Current user machine: Windows. Debian will also be used; user will announce changes.
- SEC contact: andy@andyj.tech. Prompt only for CIKs.

## Current implementation

`scan_item1c.py` retains its original filename for compatibility but defaults to
searching entire primary documents and additional HTML/text exhibits across
all available form types. Explicit
`--section item1c` restores the narrower section extraction. Historical metadata
files overlapping the date range are included in direct CIK mode. Existing CSV
inventories retain their own coverage limits. `edgar_inventory.py` remains an
optional metadata-only helper with a recent-metadata default and SIC filtering.

Documents are fetched into memory; raw filing files are not saved.
Research text and evidence are saved in JSONL and CSV. Directory listings are used to discover additional HTML/text documents; the
combined full submission is skipped to avoid duplication. PDFs/images, XBRL-only
attachments, related-company filings, and confidential reports are not searched.
Use `--primary-only` for a faster pass without exhibits. Failed exhibit retrieval
marks the filing incomplete so it can be retried. Each passage retains its own
document URL; offsets and tag contexts refer to that source document. The saved
`section` text is the primary document; exhibit evidence is stored as passages.

## What a result establishes

A match is a candidate disclosure. It does not establish a fraud incident,
a perpetrator, a loss, or AI causation. The surrounding text must distinguish
hypothetical risks, controls, allegations, actual events, and statements about
materiality. No material impact does not mean no incidents.

Candidate search vocabulary also includes AI and cyber terms to discover possible
connections. These can generate unrelated matches. Review a sample of zero-match
filings for missed terminology before comparing disclosure prevalence.

Results include negative and failed records. Failure, unavailable text, missing
Item 1C, and a successful zero-keyword scan must remain distinct. A no-readable-text
result makes the command return failure. Overlapping passage chunks and repeated
filing updates do not represent distinct incidents.

## XBRL limits

Visible `ix:nonNumeric` and `ix:nonFraction` elements enclosing passages are
recorded, with names, context references, units where present, and offsets.
Tag names preserve the source spelling. Untagged passages have an empty tag list.
A text-block concept is not necessarily a standardized fraud expense.

Continued fact chains are flagged but not resolved. Full taxonomy definitions,
numeric transformations, dimensions, and accounting comparability remain future
work. Do not aggregate a tag's values without checking the underlying disclosure.

## Item 1C limits

Compliance began with fiscal years ending on or after December 15, 2023. Earlier
years need other sections; the full-document default allows that search.
Section-specific extraction is heuristic, requires a closing Item 1D/2 heading,
and must be checked on real filings. Missing Item 1C is not zero fraud.
8-K Item 1.06 is Material Cybersecurity Incidents; Item 8.01 is Other Events.
There is no current 8-K Item 1.05.

## OpenAI

Optional paid analysis requires explicit `--llm`, model selection, and an API key
in the environment. JSON fields and exact evidence quotations are checked, but
that does not prove an interpretation correct. Model, prompt version, usage, and
review status accompany each response. No automated dollar aggregation occurs.

## Next research steps

1. Inspect one company's spreadsheet and verify source passages.
2. Refine fraud vocabulary and categories, including financial-impact labels.
3. Review exhibit evidence and decide whether PDF/image extraction is needed.
4. Map CIKs/subsidiaries to a dated S&P 500 Financials constituent list.
5. Deduplicate events and comparable accounting amounts before sector analysis.

## Validation

Run `python -m unittest discover -s tests -v` on Windows, or `python3` on Debian.
Tests cover full-document matches outside Item 1C, other form types, resumption,
historical metadata, no-argument CIK input, tags, missing sections, local CLI,
metadata errors, and rejection of invented LLM quotations. Network calls are
mocked in these tests; passing them does not establish live SEC/OpenAI access.


## Financial-amount discovery and pilot

The default focus is now financial. Explicit fraud indicators seed passages;
AI/cyber words alone no longer trigger them. Use `--focus discovery` for the
older broad vocabulary. Monetary candidates must share a sentence with an
explicit fraud indicator. This is only a candidate relationship, not verified
attribution. Ordinary credit losses without fraud context are excluded.

Amounts are kept separate by category suggestion: loss, provision/liability,
customer reimbursement, recovery, insurance recovery, fine/settlement, and
prevention/remediation cost. Mixed statements remain ambiguous. Potential
statements are flagged. There is no automatic total. Numeric magnitudes do not
resolve accounting signs, ranges, currency ambiguity, or shared table units.
A `$` marker alone is not assumed to mean USD. Quoted period and accounting
location are not inferred from filing metadata.

The amounts CSV distinguishes tags overlapping the monetary expression from
broader passage tags. A text-block tag still does not establish the accounting
line or taxonomy definition. Tests identified and corrected a text-offset
collision with Python HTMLParser's internal position tracking.

Candidate evidence is deduplicated within a filing using document URL and text
offset. Overlapping windows do not create duplicate rows for the same expression.
Repeated events across filings, multiple documents, and companies still require
review. Amount/coverage CSVs use the latest attempt per filing/scope/focus for the
current scan version; JSONL and the broad passage CSV retain attempt history.
Incomplete scans can preserve partial evidence, explicitly flagged by scan status.
Company-year prevalence requires a complete, reviewed denominator; these tables
do not calculate one automatically.

`--pilot` scans two pending filings per supplied CIK, not two filings total.
Combine with `--forms 10-K` for an annual-report pilot. `--cik-file` reads one CIK
per line or a CSV with a cik column. The included example lists JPMorgan Chase
and Bank of America only. It does not establish a full or historical S&P 500
universe. Expand using a dated constituent list and omit `--pilot` to scan all.

Optional OpenAI output now includes financial findings with exact amount text,
category, supporting quotation, accounting label, and period where stated.
Unsupported quotes, labels, periods, and non-monetary amount strings are rejected.
LLM results remain suggestions requiring human review. No live model calls were
used in the offline validation.
