# EDGAR fraud research

Search a company's EDGAR filings for fraud/cyber-related passages, preserve source
links and enclosing Inline XBRL tags, and optionally classify evidence with OpenAI.
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

## Default search

- Filing dates **2020-01-01 through 2026-12-31**, limited to filings currently available.
- **All form types** available in the company's SEC submissions metadata, including
  overlapping historical submissions files. Amendments are included.
- The **entire primary filing document** and additional HTML/text documents,
  including exhibits, rather than only Item 1C.
- All eligible filings; successful previous scans in the same output are skipped.
- Keywords include fraud, scams, account takeover, identity theft, synthetic
  identity, unauthorized transactions, phishing, social engineering, ransomware,
  AI, embezzlement, misappropriation, money laundering, and chargebacks.

This does **not** search PDFs/images, XBRL-only attachments, related companies'
CIKs, or confidential reports. Some scanned forms contain no useful narrative.
It is not an exhaustive EDGAR full-text search. Filing metadata failures and
unreadable documents remain distinguishable from successful zero-match scans.

## Outputs

Saved beside the script, regardless of the terminal's starting directory:

- `data/fraud_scan.csv`: spreadsheet with company, CIK, SIC, form, dates, source
  URL, keywords, passage text, associated XBRL tag names, and status/error.
- `data/fraud_scan.jsonl`: detailed evidence, including extracted text, document
  hashes, tag contexts, and optional model output.

Output is appended. Repeat successful filings are skipped unless `--rescan` is
used. Old runs and rescans can coexist, so deduplicate before statistical work.
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

A tag surrounding a passage may be a broad text-block tag, not a fraud accounting
measure. Definitions and contexts must be checked. See [RESEARCH.md](RESEARCH.md)
for interpretation and validation limits.

## SEC access

Requests are sequential and paced with TLS verification enabled. A 403 may be a
network-policy denial or an SEC access restriction; do not bypass either.
Network access is needed to `data.sec.gov` and `www.sec.gov`; optional OpenAI
analysis also needs `api.openai.com`.
