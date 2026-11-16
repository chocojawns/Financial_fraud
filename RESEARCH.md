# Research notes

## Agreed project scope

- Goal: investigate disclosed fraud impacts on S&P 500 Financials.
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
