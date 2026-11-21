# S&P 500 8-K fraud and cybersecurity discovery

Period: 2020-01-01 through 2026-11-21 (filing dates). Status: STOPPED / INCOMPLETE.
Companies completely scanned: 435/500. Primary filing documents scanned: 44845.




| Sector | Complete/constituents | Scanned 8-Ks | Fraud-word filings | Cyber-word filings | Item 1.06 filings | Relevant % of complete companies |
|---|---:|---:|---:|---:|---:|---:|
| Communication Services | 18/19 | 2649 | 17 | 66 | 0 | 50.0 |
| Consumer Discretionary | 43/47 | 3885 | 6 | 75 | 0 | 41.9 |
| Consumer Staples | 28/33 | 2906 | 8 | 18 | 0 | 42.9 |
| Energy | 19/21 | 1985 | 2 | 113 | 0 | 68.4 |
| Financials | 70/76 | 7709 | 93 | 196 | 0 | 60.0 |
| Health Care | 54/60 | 4954 | 21 | 164 | 0 | 50.0 |
| Industrials | 73/83 | 6408 | 20 | 345 | 0 | 45.2 |
| Information Technology | 63/76 | 5665 | 14 | 114 | 0 | 57.1 |
| Materials | 16/24 | 1937 | 6 | 58 | 0 | 43.8 |
| Real Estate | 26/30 | 3040 | 9 | 25 | 0 | 42.3 |
| Utilities | 25/31 | 3707 | 13 | 334 | 0 | 68.0 |

## What the program did

Read the bundled 500-company snapshot, retrieve recent and historical SEC metadata,
scan all available 8-K and 8-K/A primary documents in the period, identify item
numbers and fraud/cybersecurity vocabulary, and retain source excerpts. No LLM,
API key, images, raw filing downloads, or cache. Other than the bundled company
list, only result CSVs and this report are saved. Reruns start a new scan.

There is no current 8-K Item 1.05. Item 1.06 concerns material cybersecurity incidents.
Items 4.02 (financial-statement non-reliance), 5.02 (leadership changes), 7.01
(Regulation FD), 8.01 (other events), and 9.01 (exhibits) can provide context, but
are not fraud-specific. Their presence alone does not count as a relevant match.
The full primary text is searched regardless of item number. No exhibit attachments
or PDFs are searched in this version.

## How to interpret the comparison

These are disclosure counts, not confirmed attacks, fraud incidents, loss totals,
or evidence of AI causation. A filing can match both categories. One event may
produce multiple filings and amendments. Item numbers can appear in references;
body-derived items and preceding-item labels require verification against the source.
A keyword can describe a hypothetical risk, denial, boilerplate, or actual event.

Percentages use only companies whose metadata and every identified filing were
successfully scanned. Counts also retain positive findings from partial scans;
consult coverage.csv before comparing sectors. A completely scanned company with
no eligible 8-Ks is included in the company denominator. An unscanned sector is
unknown, not zero fraud. Do not rank sectors until coverage is comparable.

The company list is a third-party snapshot retrieved November 20, 2026, sourced
from Wikipedia via datasets/s-and-p-500-companies. It is not independently verified
official membership or historical membership. Share classes with the same CIK are
scanned once. Applying the snapshot to 2020 onward creates a fixed-company panel.
Item 1.06 reporting began in December 2023, so comparisons across that date reflect
changes in disclosure requirements as well as possible underlying events.

## Next research step

Review findings.csv to separate actual incidents from risks and corporate
misconduct from victimization. Deduplicate related filings into events. Then
compare sector disclosure rates and, where explicitly stated, financial impacts.
If quantities are sparse, study the specificity of disclosures rather than
claiming to measure total fraud costs. No automatic amount summation is performed.
