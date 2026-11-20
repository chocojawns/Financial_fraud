# Fraud discovery

Run `discovery.py`. No arguments, prompts, or API keys.

```powershell
python discovery.py
```

On Debian:

```bash
python3 discovery.py
```

The program uses the bundled 76-company S&P 500 Financials snapshot, collects
2020–2026 annual, quarterly, and current report text plus HTML/text exhibits, and
looks for fraud discussion and related monetary candidates. SEC requests use the
hard-coded contact **andrew@johnson.vet**. It makes no OpenAI calls at this stage.

The list is a third-party snapshot retrieved November 20, 2026, not independently
verified official membership or historical membership. Source and checksum:
`universes/sp500_financials_source.json`.

## Output

- `reports/financials_discovery.md`: readable collection summary and direction.
- `data/financials_discovery.csv`: excerpts and source links.
- `data/financials_discovery_amounts.csv`: unreviewed monetary candidates and tags.
- `data/financials_discovery_coverage.csv`: scanned filings and failures.

Successful filing scans resume automatically. Dollar amounts are not automatically
added or treated as realized fraud losses. Missing disclosures are not zero.
PDFs/images, XBRL-only attachments, and confidential reports are not searched.

## Proof of concept already run

Read [the POC report](reports/proof_of_concept/DISCOVERY.md) for actual baseline
numbers, the method, limitations, and the next experiment. It uses the user's
supplied healthcare/industrial Item 1A text—not Financials results and not LLM output.

To reproduce that baseline, put the original `item_1a_results.json` in `inputs/`.
Running `discovery.py` produces the baseline first, then attempts Financials collection.
Raw input is ignored by Git. The source checksum is included in the POC manifest.

## Current blocker

This cloud environment currently denies SEC requests. Enable `data.sec.gov` and
`www.sec.gov` in its settings. The program records a clear blocked report rather
than claiming zero fraud. The same program can run on Windows or Debian where
SEC access is permitted.

## Tests

```bash
python -m unittest discover -s tests -v
```

The older scanner is retained as an internal helper in `_edgar_scanner.py`.
There is no need to run it or supply its advanced options. LLM integration can
be revisited after the discovery evidence supports a specific research direction.
