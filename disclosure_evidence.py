"""Descriptive text signals and company-year coverage, not fraud adjudication."""
import csv
import hashlib
from pathlib import Path
import re

MONEY = re.compile(r'(?:US\$|USD|EUR|GBP|\$|€|£)\s*\d+(?:,\d{3})*(?:\.\d+)?'
                   r'\s*(?:billion|million|thousand|bn|mm|m|b|k)?(?!\w|\.\d)', re.I)
COST = re.compile(r'\b(?:loss(?:es)?|costs?|expenses?|remediation|reimburs\w*|'
                  r'recoveries|recovery|fines?|penalt\w*|settlement\w*|provisions?)\b', re.I)
SIGNALS = {
    'risk_language': r'\b(?:may|might|could|potential|risk factors?|forward[- ]looking)\b',
    'event_language': r'\b(?:identified|discovered|experienced|incurred|detected|reported|notified)\b',
    'allegation_language': r'\b(?:alleg\w*|lawsuits?|complaints?|investigations?)\b',
    'contract_language': r'\b(?:indemnif\w*|representations and warranties|escrow|merger agreement)\b',
}


def financial_windows(text, patterns):
    """Keep cost paragraphs that can sit far from an original fraud keyword."""
    windows = []
    for money in MONEY.finditer(text):
        left, right = max(0, money.start() - 1000), min(len(text), money.end() + 1000)
        context = text[left:right]
        linked = any(pattern.search(context) for pattern in patterns.values())
        incident_reference = re.search(r'\b(?:this|the|that) incident\b', context, re.I)
        if linked or (incident_reference and COST.search(context)):
            windows.append((left, right))
    return windows


def describe(text):
    normalized = re.sub(r'\s+', ' ', text).strip().lower()
    # Keep numbers: changing amounts must not be silently treated as identical.
    return dict({name: bool(re.search(pattern, text, re.I)) for name, pattern in SIGNALS.items()},
                evidence_fingerprint=hashlib.sha256(normalized.encode()).hexdigest()[:20],
                financial_terms='; '.join(sorted({m.group().lower() for m in COST.finditer(text)})),
                review_status='unreviewed')


def amount_rows(passage):
    for match in MONEY.finditer(passage['text']):
        yield {'amount_text': match.group().strip(),
               'amount_offset': passage['offset'] + match.start(),
               'association': 'nearby_text_candidate_not_verified',
               'review_status': 'unreviewed'}


def write_company_years(folder, coverage, eligible_years, first_year, last_year):
    """A filing-year panel; no fiscal-year or incident-date inference."""
    panel = {}
    for company in coverage:
        for year in range(first_year, last_year + 1):
            key = (company['cik'], year)
            panel[key] = {k: company[k] for k in ['cik', 'ticker', 'company', 'sector']}
            panel[key].update(filing_year=year, eligible_filings=eligible_years.get(key, ''),
                              scanned_filings=0, failed_filings=0, annual_filings=0,
                              quarterly_filings=0, current_filings=0, fraud_filings=0,
                              cyber_filings=0, item_1_05_filings=0, status='unknown')
    source = folder / 'filings.csv'
    if source.exists():
        with source.open(encoding='utf-8-sig', newline='') as input_file:
            for filing in csv.DictReader(input_file):
                row = panel[(filing['cik'], int(filing['filing_date'][:4]))]
                if filing['status'] != 'scanned':
                    row['failed_filings'] += 1
                    continue
                row['scanned_filings'] += 1
                column = {'10-K': 'annual_filings', '10-Q': 'quarterly_filings',
                          '8-K': 'current_filings'}[filing['form'].split('/')[0]]
                row[column] += 1
                for field, column in [('fraud_match', 'fraud_filings'), ('cyber_match', 'cyber_filings'),
                                      ('item_1_05', 'item_1_05_filings')]:
                    row[column] += int(filing[field] == 'True')
    for row in panel.values():
        expected = row['eligible_filings']
        if expected == '':
            row['status'] = 'unknown_metadata'
        elif expected == 0:
            row['status'] = 'no_filings_in_window'
        elif row['scanned_filings'] == expected:
            row['status'] = 'complete'
        else:
            row['status'] = 'incomplete'
    with (folder / 'company_year.csv').open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=list(next(iter(panel.values()))))
        writer.writeheader()
        writer.writerows(panel.values())
