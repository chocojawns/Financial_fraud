# EDGAR fraud research

Research question: **Which companies separately disclose fraud-related financial
amounts, what do those amounts represent, and where are they reported?**

Search EDGAR filings for explicit fraud language and monetary candidates, preserve
quotes and XBRL tags, and optionally classify the evidence with OpenAI.
Python 3.10+; no third-party packages required.

## Start in VS Code — Windows

1. Open `scan_item1c.py`.
2. Click **Run Python File in Terminal**.
3. Enter the company's numeric CIK, e.g. `1818874` for SoFi.

Only the CIK is requested. SEC requests use `FraudResearch andy@andyj.tech`.
No OpenAI key is required and no paid calls occur by default.

Or run from the repository folder in PowerShell:

```powershell
python .\scan_item1c.py
```

If your terminal is in the parent folder:

```powershell
python .\Financial_fraud\scan_item1c.py
```

## Debian

Open the same repository folder and run:

```bash
python3 scan_item1c.py
```

Both operating systems use the same code and outputs. The user's current machine
is Windows; Debian will also be used during this project.

## Start with two companies, then scale

From the repository folder on Windows:

```powershell
# Two latest pending annual reports per company: JPMorgan Chase and Bank of America
python scan_item1c.py --cik-file examples/pilot_ciks.txt --forms 10-K --pilot
```

Review `data/fraud_financials_amounts.csv` and `data/fraud_financials_coverage.csv`.
Every amount starts as **unreviewed**, not a confirmed fraud loss. Copy the amounts
CSV to a separate review file before editing it; generated reports are rebuilt.

To scale, create `financials_ciks.txt` with one numeric CIK per line, using a
dated S&P 500 Financials membership list. Then run:

```powershell
python scan_item1c.py --cik-file financials_ciks.txt --forms 10-K 10-K/A 10-Q 10-Q/A 8-K 8-K/A
```

A CSV with a `cik` column also works. The program does not invent a constituent
list. Omit `--pilot` to scan all qualifying filings. It resumes successful filings
from the same output; failed/incomplete ones are retried. On Debian use `python3`.

## Default search

- Filing dates **2020-01-01 through 2026-12-31**, limited to filings currently available.
- **All form types** available in the company's SEC submissions metadata, including
  overlapping historical submissions files. Amendments are included.
- The **entire primary filing document** and additional HTML/text documents,
  including exhibits, rather than only Item 1C.
- All eligible filings; successful previous scans in the same output are skipped.
- Default financial focus searches explicit fraud indicators: fraud, scams,
  account takeover, identity theft, synthetic identity, unauthorized transactions,
  business email compromise, embezzlement, and misappropriation.
- `--focus discovery` restores the broader AI/cyber keyword exploration.

This does **not** search PDFs/images, XBRL-only attachments, related companies'
CIKs, or confidential reports. Some scanned forms contain no useful narrative.
It is not an exhaustive EDGAR full-text search. Filing metadata failures and
unreadable documents remain distinguishable from successful zero-match scans.

## Outputs

Saved beside the script, regardless of the terminal's starting directory:

- `data/fraud_financials_amounts.csv`: one row per monetary candidate, supporting
  quote, suggested category, currency marker, numeric magnitude, review status,
  and tags on the amount versus elsewhere in its passage.
- `data/fraud_financials_coverage.csv`: filing coverage, errors, and whether the
  scan found candidate amounts, fraud discussion without an amount, or no fraud terms.
- `data/fraud_financials.csv`: spreadsheet with company, CIK, SIC, form, dates, source
  URL, keywords, passage text, associated XBRL tag names, and status/error.
- `data/fraud_financials.jsonl`: detailed evidence, including extracted text, document
  hashes, tag contexts, and optional model output.

Output is appended. Repeat successful filings are skipped unless `--rescan` is
used. Amount/coverage reports select the latest attempt per filing/scope/focus
for the current scan version. The broad passage CSV includes the full run history.
Different filings can repeat the same loss; deduplicate events before statistical work.
Passage windows can overlap; they are **not distinct incident counts**.

## Useful commands

```powershell
# A quick first test
python scan_item1c.py --ciks 1818874 --limit 1

# Faster pass without exhibits
python scan_item1c.py --ciks 1818874 --primary-only

# Only annual, quarterly, and current reports, including amendments
python scan_item1c.py --ciks 1818874 --forms 10-K 10-K/A 10-Q 10-Q/A 8-K 8-K/A

# Multiple companies
python scan_item1c.py --ciks 19617 70858 72971

# Item 1C only
python scan_item1c.py --ciks 1818874 --forms 10-K --section item1c

# Local HTML: no SEC connection required
python scan_item1c.py --html company-10k.htm

# Optional paid analysis: set OPENAI_API_KEY securely first
python scan_item1c.py --ciks 1818874 --limit 1 --llm --model YOUR_MODEL

# Tests
python -m unittest discover -s tests -v
```

On Debian use `python3` in place of `python`. Set `--since` and `--until` to
change filing dates; they do not select fiscal years or incident dates.
Use `--output data/my-run.jsonl` for a separate research run. The tool creates
its companion CSV. SEC contact can be overridden with `--email` or
`SEC_USER_AGENT`. The scripts do not automatically load `.env` files.

OpenAI credentials belong in secure environment variables, never Git or chat.
Calls require explicit `--llm` and a compatible model supporting Chat Completions
JSON object output. A large filing can contain many billable passages: `--limit`
caps filings, not API calls. Start small.

## Research goal and limits

The goal is to investigate fraud's impact on **S&P 500 Financials**. A CIK scan
is one company's evidence collection, not a sector-wide result. SIC codes are
retained as metadata, not used to exclude a requested company. There is no
current S&P 500/GICS membership filter; companies and subsidiaries must be
mapped to a dated constituent list before making sector claims.

Keyword matches may describe hypothetical risks, controls, allegations, or
actual incidents. AI/cyber mentions are not automatically fraud. Missing
financial amounts are not zero. Disclosed losses, provisions, reimbursements,
fines, insurance recoveries, and prevention spending need separate review.

Amounts are found through fraud/money co-occurrence within a sentence, not by
assuming every number near fraud is a loss. Even this co-occurrence can be
misleading: review attribution, whether the company bore the cost, and the period.
Ordinary credit losses/defaults without explicit fraud language do not qualify.
Tables, shared units, and indirect references can be missed. Currency stays
unknown when only `$` is present; normalized numbers are magnitudes, not signed
accounting facts. There is no automatic sum or fraud-loss total.

Suggested categories distinguish losses, provisions/liabilities, reimbursements,
recoveries, insurance recoveries, fines/settlements, and prevention/remediation
costs. Mixed evidence remains ambiguous. Accounting line and amount period stay
blank unless explicitly supported in optional LLM output or filled by a reviewer;
the filing date is never substituted for the amount's reporting period.

A tag surrounding a passage may be a broad text-block tag, not a fraud accounting
measure. Definitions and contexts must be checked. See [RESEARCH.md](RESEARCH.md)
for interpretation and validation limits.

## SEC access

Requests are sequential and paced with TLS verification enabled. A 403 may be a
network-policy denial or an SEC access restriction; do not bypass either.
Network access is needed to `data.sec.gov` and `www.sec.gov`; optional OpenAI
analysis also needs `api.openai.com`.
