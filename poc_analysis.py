"""Small, reproducible baseline. Counts text matches, never fraud incidents."""
import csv
import hashlib
import json
from pathlib import Path
import re
from collections import Counter

from fraud_financials import FRAUD, MONEY, financial_candidates


def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_poc(input_path, folder):
    folder.mkdir(parents=True, exist_ok=True)
    records = json.loads(input_path.read_text(encoding='utf-8'))
    rows, examples = [], []
    for record in records:
        text = record.get('item_1a_text') or ''
        readable = record.get('status') == 'ok' and bool(text.strip())
        literal = bool(re.search(r'\bfraud\w*\b', text, re.I)) if readable else False
        broad = bool(FRAUD.search(text)) if readable else False
        money = list(MONEY.finditer(text)) if readable else []
        amounts = financial_candidates({'text': text, 'start': 0,
                                        'document_url': record.get('source_url', '')}) if readable else []
        rows.append({'sector': record.get('sector', ''), 'ticker': record.get('ticker', ''),
                     'cik': record.get('cik', ''), 'accession': record.get('accession_number', ''),
                     'readable': readable, 'literal_fraud': literal, 'broad_indicator': broad,
                     'money_expressions': len(money), 'fraud_money_candidates': len(amounts),
                     'source_url': record.get('source_url', '')})
        if literal:
            match = re.search(r'\bfraud\w*\b', text, re.I)
            examples.append({'ticker': record.get('ticker', ''), 'sector': record.get('sector', ''),
                             'quote': text[max(0, match.start() - 180):match.end() + 650],
                             'source_url': record.get('source_url', '')})
    write_csv(folder / 'filing_results.csv', rows, list(rows[0]))
    write_csv(folder / 'evidence.csv', examples, ['ticker', 'sector', 'quote', 'source_url'])
    summary = []
    for sector in sorted({r['sector'] for r in rows}):
        group = [r for r in rows if r['sector'] == sector]
        valid = [r for r in group if r['readable']]
        literal = sum(r['literal_fraud'] for r in valid)
        summary.append({'sector': sector, 'records': len(group), 'readable': len(valid),
                        'failed_or_empty': len(group) - len(valid), 'literal_fraud': literal,
                        'literal_fraud_percent': round(100 * literal / len(valid), 1) if valid else None,
                        'broad_indicator': sum(r['broad_indicator'] for r in valid),
                        'money_expressions': sum(r['money_expressions'] for r in valid),
                        'fraud_money_candidates': sum(r['fraud_money_candidates'] for r in valid)})
    write_csv(folder / 'sector_summary.csv', summary, list(summary[0]))
    total = len(rows)
    readable = sum(r['readable'] for r in rows)
    literal = sum(r['literal_fraud'] for r in rows)
    broad = sum(r['broad_indicator'] for r in rows)
    money = sum(r['money_expressions'] for r in rows)
    amounts = sum(r['fraud_money_candidates'] for r in rows)
    manifest = {'input_file': input_path.name, 'input_sha256': hashlib.sha256(input_path.read_bytes()).hexdigest(),
                'records': total, 'readable_records': readable, 'literal_fraud_records': literal,
                'broad_indicator_records': broad, 'money_expressions': money,
                'fraud_money_candidates': amounts, 'llm_calls': 0,
                'method': 'Regex baseline on user-supplied Item 1A extraction; no live SEC verification',
                'unique_ciks': len({r['cik'] for r in rows}),
                'unique_accessions': len({r['accession'] for r in rows})}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    table = '\n'.join(f'| {s["sector"]} | {s["records"]} | {s["readable"]} | '
                      f'{s["literal_fraud"]} ({s["literal_fraud_percent"]}%) | '
                      f'{s["broad_indicator"]} | {s["fraud_money_candidates"]} |' for s in summary)
    report = f'''# Fraud disclosure discovery: proof of concept

**Status: real text-mining baseline, not a financial-sector fraud-loss estimate.**

## What was run and why

The supplied `item_1a_results.json` contains {total} healthcare/industrial filing
records. {readable} contain text marked successful by the original extraction.
The remaining {total - readable} were excluded from text-percentage denominators.
This POC tests whether risk-factor text can support the proposed financial-impact
question before spending time or money on a larger collection or LLM analysis.

The program reads text, counts literal fraud language and a broader indicator
list, and looks for monetary expressions in the same sentence as a fraud indicator.
It saves one filing-level row and linked source excerpts. It makes **no OpenAI calls**.

## Measured results

| Supplied sector | Input records | Readable records | Literal fraud language | Broader indicators | Same-sentence monetary candidates |
|---|---:|---:|---:|---:|---:|
{table}

Across the readable records, {literal} contain literal fraud language and {broad}
contain the broader indicator vocabulary. The text contains {money} recognized
monetary expressions overall, but only {amounts} meet the strict fraud/money
same-sentence rule. These are text-mining counts, not incident counts or dollars.

## What this tells us

1. Fraud discussion is common enough in this supplied text to study disclosure.
2. A broad vocabulary changes the results substantially. Misappropriation can,
   for example, concern intellectual property rather than a company fraud loss.
3. Finding dollar figures is different from attributing them to fraud. This
   method does not establish a fraud-loss total.
4. Item 1A alone appears insufficient for the financial-impact question in this
   sample. Next examine financial-statement notes, MD&A, and relevant 8-K exhibits.

## Specific direction to test next

**Do financial companies quantify fraud as a business cost, or primarily describe
it as a risk—and how does that differ across banking, payments, and insurance?**

The next small pilot should distinguish a company as victim, alleged perpetrator,
fraud-prevention provider, or a business discussing regulatory exposure. It should
separate realized losses, potential liabilities, reimbursements, recoveries, fines,
and prevention costs. Ordinary customer defaults remain outside the question
unless the disclosure explicitly attributes them to fraud.

This is a proposed direction, not a result about those financial subsectors.

## What I would change before presenting substantive findings

- Manually review 10–15 excerpts to assess whether the vocabulary captures the
  intended type of fraud. The complete evidence table is `evidence.csv`.
- Test a few Financials companies' full 10-Ks and event disclosures. Review notes
  and MD&A rather than assuming Item 1A provides financial amounts.
- Once the labels are clear, use an LLM to classify longer passages and extract
  supported amounts. Check the output against a manually reviewed sample.
- If explicit amounts remain too sparse, make disclosure specificity/transparency
  the measured outcome rather than estimating total fraud losses.

## Presentation readiness

This baseline is ready to explain the method, show actual counts, and justify a
next experiment. It is not ready to establish industry losses, trends, or AI effects.
For a graded research presentation, complete the manual review and small Financials
pilot first, then finalize the question. Set the presentation date after those
checks rather than promising a date before knowing whether the data support it.

## Limits

The supplied dataset is healthcare/industrials, not Financials. Sector labels and
extractions were supplied by the user and have not been independently verified.
There is no claim that this is a complete/random S&P 500 sample. Accession dates
are not incident dates or fiscal years; this is not a longitudinal trend analysis.
Literal mentions are not verified fraud. Missing text is not zero exposure.
Same-sentence matching misses tables, shared units, and amounts in other sections.
Repeated values must not be added across filings. No causal or significance claim
is made from the sector percentages.

## Reproduce

Place the original JSON in `inputs/item_1a_results.json`, then run `discovery.py`.
The input checksum is in `manifest.json`. The baseline is built from the supplied
text and works even if SEC access is unavailable. The program then attempts the
Financials collection separately and labels any access failure.
'''
    (folder / 'DISCOVERY.md').write_text(report, encoding='utf-8')
    print('POC report:', folder / 'DISCOVERY.md')
    print(f'{total} input records; {readable} readable; {literal} literal fraud matches; '
          f'{amounts} same-sentence money candidates. No LLM used.')
    return manifest


def write_financials_report(path, report, error=None):
    report.parent.mkdir(parents=True, exist_ok=True)
    if error:
        report.write_text('# Financials discovery — blocked\n\n'
                          'SEC access failed before financial filing collection. No industry findings '
                          'or fraud-loss estimates can be reported. No OpenAI calls were made.\n\n'
                          f'Observed error: `{error}`\n\n'
                          'Allow data.sec.gov and www.sec.gov in the running cloud environment, '
                          'or run the same program on your machine.\n', encoding='utf-8')
        return
    latest = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        record = json.loads(line)
        filing = record.get('filing', {})
        latest[(filing.get('cik', record.get('cik')), filing.get('accession'))] = record
    records = list(latest.values())
    status = Counter(r.get('status') for r in records)
    rows = [r for r in records if r.get('status') == 'extracted_needs_review']
    companies = {r['filing']['cik'] for r in rows}
    candidates = sum(r.get('financial_candidate_count', 0) for r in rows)
    report.write_text(f'''# Financials disclosure discovery

Run on the bundled 76-company, third-party Financials snapshot retrieved November
20, 2026. This is a fixed panel, not historical S&P 500 membership.

- Successful filing scans: {len(rows)}
- Companies with a successful filing scan: {len(companies)}
- Scan/error statuses: {dict(status)}
- Unreviewed monetary candidates in successful scans: {candidates}
- OpenAI calls in this discovery workflow: 0

The program searched 2020–2026 annual, quarterly, and current reports and HTML/text
exhibits. It used explicit fraud indicators, retained context and source links,
and recorded financial candidates and XBRL tags. PDFs/images and confidential
reports were excluded. A successful keyword scan is not proof of fraud.

Review the companion `_amounts.csv` and `_coverage.csv` beside `{path.name}`.
Separate realized losses from hypothetical exposures, reimbursements, recoveries,
fines, prevention costs, and unrelated credit losses. This report does not sum
unreviewed amounts or claim industry incidence. Incomplete scans are not zero.

The next decision is whether sufficiently comparable amounts exist for an impact
study. Otherwise, measure disclosure specificity and accounting transparency.
''', encoding='utf-8')
