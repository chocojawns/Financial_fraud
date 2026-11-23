"""DRAFT: review fraud-related cost disclosures. Run without arguments or keys."""
import csv
from datetime import date, datetime
import hashlib
from pathlib import Path
import re

from disclosure_evidence import MONEY
from discovery import SEC, PATTERNS, access_block, extract_text, get_filings, safe

ROOT = Path(__file__).resolve().parent
# Begin with two documented cases. Expand this list after reviewing the pilot.
COMPANIES = [('1679788', 'COIN', 'Coinbase'), ('35527', 'FITB', 'Fifth Third')]
COST_WORDS = re.compile(r'\b(?:loss(?:es)?|expenses?|costs?|remediation|reimburs\w*|'
                        r'fines?|penalt\w*|settlement\w*|provisions?|recover\w*|damages)\b', re.I)
CATEGORIES = {
    'loss': r'\bloss(?:es)?\b',
    'response_cost': r'\b(?:remediation|investigation costs?|response costs?)\b',
    'customer_reimbursement': r'\breimburs\w*\b',
    'fine_or_settlement': r'\b(?:fines?|penalt\w*|settlement\w*)\b',
    'provision_or_liability': r'\b(?:provisions?|accru\w*|liabilit\w*)\b',
    'recovery': r'\brecover\w*\b',
    'prevention_spending': r'\b(?:prevention|monitoring|security)\s+(?:costs?|expenses?|spending)\b',
    'damages_award_or_claim': r'\bdamages\b',
}


def find_cost_candidates(text):
    """Co-occurrence identifies leads, never confirmed attribution or amounts spent."""
    has_cyber = bool(PATTERNS['cybersecurity'].search(text))
    regulatory_document = bool(re.search(r'\b(?:CFPB|Consumer Financial Protection Bureau|'
                                         r'consent order|stipulated final judgment)\b', text, re.I))
    for amount in MONEY.finditer(text):
        near = text[max(0, amount.start() - 250):amount.end() + 250]
        if not COST_WORDS.search(near):
            continue
        left, right = max(0, amount.start() - 900), min(len(text), amount.end() + 900)
        quote = text[left:right]
        if PATTERNS['fraud'].search(quote):
            link = 'fraud_vocabulary_nearby_unverified'
        elif (PATTERNS['cybersecurity'].search(quote)
              or has_cyber and re.search(r'\b(?:this|the|that) incident\b', quote, re.I)):
            link = 'cyber_incident_context_not_automatically_fraud'
        elif regulatory_document and re.search(r'\b(?:civil monetary penalty|consent order|redress)\b', quote, re.I):
            link = 'regulatory_context_not_verified_fraud'
        else:
            continue
        labels = [name for name, pattern in CATEGORIES.items() if re.search(pattern, near, re.I)]
        flags = []
        for name, pattern in {
            'estimate_or_conditional_words': r'\b(?:estimat\w*|approximately|may|could|potential|range)\b',
            'accrual_words': r'\b(?:accru\w*|recognized|recorded|provision)\b',
            'payment_words': r'\b(?:paid|payment|cash)\b',
            'agreement_words': r'\b(?:agreed|agreement|order)\b',
        }.items():
            if re.search(pattern, near, re.I):
                flags.append(name)
        marker = re.match(r'(?:US\$|USD|EUR|GBP|\$|€|£)', amount.group(), re.I).group()
        currency = {'USD': 'USD', 'US$': 'USD', 'EUR': 'EUR', '€': 'EUR',
                    'GBP': 'GBP', '£': 'GBP'}.get(marker.upper(), 'unknown')
        yield {
            'amount_text': amount.group().strip(), 'currency': currency,
            'category_hint': labels[0] if len(labels) == 1 else 'mixed_or_unclear',
            'category_options': '; '.join(labels), 'accounting_basis_flags': '; '.join(flags),
            'fraud_connection_hint': link, 'quote': quote, 'amount_offset': amount.start(),
            'amount_reporting_year': '', 'accounting_basis_reviewed': '', 'event_id': '',
            'review_status': 'unreviewed', 'approved_for_totals': False, 'review_notes': '',
            'quote_fingerprint': hashlib.sha256(re.sub(r'\s+', ' ', quote).lower().encode()).hexdigest()[:20],
        }


def main():
    folder = ROOT / 'results' / ('fraud_costs_' + datetime.now().strftime('%Y-%m-%d_%H%M%S_%f'))
    folder.mkdir(parents=True)
    until = date.today().isoformat()
    base = ['company', 'ticker', 'cik', 'form', 'accession', 'filing_date', 'filing_year',
            'report_date', 'source_url']
    extra = ['amount_text', 'currency', 'category_hint', 'category_options', 'accounting_basis_flags',
             'fraud_connection_hint', 'quote', 'amount_offset', 'amount_reporting_year',
             'accounting_basis_reviewed', 'event_id', 'review_status', 'approved_for_totals',
             'review_notes', 'quote_fingerprint']
    coverage = []
    candidate_count = 0
    blocked = ''
    sec = SEC()
    print('DRAFT fraud-cost review: Coinbase and Fifth Third; 2020 through today.')
    print('No arguments, keys, LLM, raw filing storage, or automatic dollar totals.')
    try:
        with (folder / 'candidate_costs.csv').open('w', encoding='utf-8-sig', newline='') as output:
            writer = csv.DictWriter(output, fieldnames=base + extra)
            writer.writeheader()
            for cik, ticker, company in COMPANIES:
                print(ticker, 'metadata...', flush=True)
                try:
                    filings = get_filings(sec, cik, until)
                except Exception as error:
                    coverage.append({'company': company, 'cik': cik, 'form': '', 'accession': '',
                                     'filing_date': '', 'status': 'metadata_error', 'candidates': '', 'error': str(error)})
                    if access_block(error):
                        blocked = str(error)
                        break
                    continue
                for index, filing in enumerate(filings, 1):
                    row = {'company': company, 'ticker': ticker, 'cik': cik,
                           **{key: filing.get(key, '') for key in base if key not in {'company', 'ticker', 'cik'}},
                           'filing_year': filing['filing_date'][:4]}
                    status, error_message, count = 'scanned', '', 0
                    try:
                        text = extract_text(sec.read(filing['source_url']).decode('utf-8', errors='replace'))
                        if not text:
                            raise ValueError('No readable filing text')
                        for finding in find_cost_candidates(text):
                            writer.writerow(safe({**row, **finding}))
                            count += 1
                        candidate_count += count
                        output.flush()
                    except Exception as error:
                        status, error_message = 'error', str(error)
                        if access_block(error):
                            blocked = str(error)
                    coverage.append({'company': company, 'cik': cik, 'form': filing['form'],
                                     'accession': filing['accession'], 'filing_date': filing['filing_date'],
                                     'status': status, 'candidates': count, 'error': error_message})
                    print(f'  {index}/{len(filings)}: {filing["form"]} {filing["filing_date"]}: {count} leads', flush=True)
                    if blocked:
                        break
                if blocked:
                    break
    except KeyboardInterrupt:
        blocked = 'Stopped by user; partial run.'
    finally:
        fields = ['company', 'cik', 'form', 'accession', 'filing_date', 'status', 'candidates', 'error']
        with (folder / 'coverage.csv').open('w', encoding='utf-8-sig', newline='') as output:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(safe(row) for row in coverage)
        successes = sum(row['status'] == 'scanned' for row in coverage)
        failures = len(coverage) - successes
        (folder / 'REVIEW.md').write_text(f'''# Draft fraud-cost review

Pilot companies: Coinbase and Fifth Third. Forms: 10-K, 10-Q, 8-K and amendments.
Filing-date window: 2020 through {until}. Successful documents: {successes}.
Failed documents/metadata requests: {failures}. Unreviewed amount candidates: {candidate_count}.
{'Stopped: ' + blocked if blocked else 'Collection loop finished; check coverage for individual failures.'}

This is a review worksheet, not an annual fraud-spending estimate. An unstarted
company or missing document is unknown. No dollar amounts have been added.
Primary filing text only: no exhibits, images, or confidential reports.

## Review candidate_costs.csv

1. Check the exact quotation and SEC link; neighboring amounts may be unrelated.
2. Establish whether this concerns fraud, cyber only, regulatory exposure, or neither.
3. Assign an event_id so later filings and amendments can be linked to the same event.
4. Separate loss, remediation, reimbursement, provision, fine, recovery, prevention,
   and damages awards. Category hints are word matches, not verified labels.
5. Fill amount_reporting_year and accounting_basis_reviewed from explicit evidence.
   Filing year and report date do not establish when an expense or cash payment occurred.
6. Keep estimates/ranges separate from realized expenses, agreed obligations, and cash paid.
7. Copy the worksheet to a reviewed file; set approved_for_totals only after validating
   attribution, currency, amount units, period, and duplicate/YTD reporting.

Potential/contractual amounts, company revenues, recoveries, and customer funds
are not automatically company fraud costs. A bare dollar symbol leaves currency
unknown. Currency-free numbers and table units may be missed. The same amount can
appear in multiple filings and must not be added repeatedly. No candidate does
not mean no cost. Regulatory matters are deliberately separate, not proof of fraud.

The pilot is ready for fine-tuning after reviewing a small set of leads, before
expanding companies or making annual/sector comparisons. No OpenAI calls occurred.
''', encoding='utf-8')
    print('Review folder:', folder)
    return int(bool(blocked) or any(row['status'] != 'scanned' for row in coverage))


if __name__ == '__main__':
    raise SystemExit(main())
