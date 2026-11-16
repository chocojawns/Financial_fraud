"""Conservative candidate discovery, not automated fraud-loss accounting."""
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re


VERSION = 'fraud-financial-v1'
FRAUD = re.compile(r'\b(?:fraud\w*|scams?|embezzl\w*|misappropriat\w*|'
                   r'account\s+takeovers?|identity\s+theft|synthetic\s+identit\w*|'
                   r'unauthori[sz]ed\s+transactions?|business\s+e[- ]?mail\s+compromise)\b', re.I)
MONEY = re.compile(
    r'(?<![\w.])(?:(?P<currency>US\$|USD|EUR|GBP|\$|€|£)\s*'
    r'(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)\s*(?P<scale>billion|million|thousand|bn|mm|m|b|k)?(?!\w|\.\d)'
    r'|(?P<bare>\d+(?:,\d{3})*(?:\.\d+)?)\s+(?P<bare_scale>billion|million|thousand)\b)', re.I)
CATEGORIES = {
    'insurance_recovery': r'\b(?:insurance\s+recover\w*|insurance\s+proceeds)\b',
    'recovery': r'\brecover(?:y|ies|ed)\b',
    'customer_reimbursement': r'\b(?:reimburs\w*|refund\w*)\b',
    'fine_or_settlement': r'\b(?:fines?|penalt\w*|settlements?)\b',
    'provision_or_liability': r'\b(?:provisions?|accru\w*|reserves?|liabilit\w*)\b',
    'prevention_or_remediation_cost': r'\b(?:prevention|remediation|investigation|security)\s+(?:costs?|expenses?|spending)\b',
    'loss': r'\b(?:loss(?:es)?|write[- ]?offs?|charge[- ]?offs?)\b',
}


def financial_candidates(passage):
    """Require a fraud indicator and a money expression in the same sentence.

    Co-occurrence is explicitly a candidate association. It cannot establish
    attribution, loss realization, accounting location, or reporting period.
    """
    text = passage['text']
    findings = []
    boundaries = [0] + [m.end() for m in re.finditer(r'(?<=[.!?])\s+(?=[A-Z])|\n{2,}', text)] + [len(text)]
    for left, right in zip(boundaries, boundaries[1:]):
        sentence = text[left:right]
        if not FRAUD.search(sentence):
            continue
        categories = [key for key, pattern in CATEGORIES.items() if re.search(pattern, sentence, re.I)]
        if 'insurance_recovery' in categories and 'recovery' in categories:
            categories.remove('recovery')
        category = categories[0] if len(categories) == 1 else 'ambiguous_or_other'
        hypothetical = bool(re.search(r'\b(?:may|might|could|potential|hypothetical|up to)\b', sentence, re.I))
        for match in MONEY.finditer(sentence):
            currency = match.group('currency') or ''
            # A bare dollar sign does not establish USD.
            currency_code = {'US$': 'USD', 'USD': 'USD', 'EUR': 'EUR', '€': 'EUR',
                             'GBP': 'GBP', '£': 'GBP'}.get(currency.upper(), '')
            scale = (match.group('scale') or match.group('bare_scale') or '').lower()
            value = match.group('value') or match.group('bare')
            normalized = Decimal(value.replace(',', '')) * {
                '': 1, 'thousand': 1000, 'k': 1000, 'million': 1000000,
                'm': 1000000, 'mm': 1000000, 'billion': 1000000000,
                'b': 1000000000, 'bn': 1000000000}[scale]
            # Shared-scale ranges need review; do not normalize "$10" in
            # "between $10 and $20 million" as ten dollars.
            shared_scale = not scale and bool(re.match(r'\s*(?:and|to|[-–])\s*', sentence[match.end():], re.I))
            amount_start = passage.get('document_section_offset', 0) + passage.get('start', 0) + left + match.start()
            amount_end = amount_start + len(match.group())
            source = passage.get('document_url', '')
            evidence_id = hashlib.sha256(f'{source}|{amount_start}|{match.group()}'.encode()).hexdigest()[:20]
            findings.append({
                'evidence_id': evidence_id, 'amount_text': match.group().strip(),
                'normalized_number': '' if shared_scale else str(normalized),
                'currency': currency_code, 'currency_marker': currency,
                'category_candidate': category, 'category_options': categories,
                'statement_basis': 'potential_or_conditional' if hypothetical else 'requires_review',
                'association': 'same_sentence_candidate_not_verified',
                'evidence_quote': sentence.strip(), 'source_url': source,
                'amount_offset': amount_start, 'accounting_location': '',
                'amount_reporting_period': '', 'review_status': 'unreviewed',
                'llm_category': '',
                'amount_xbrl_tags': [fact for fact in passage.get('tags', [])
                                     if fact.get('start', 0) < amount_end
                                     and fact.get('end', 0) > amount_start],
            })
    return findings


def enrich(record):
    seen = set()
    count = 0
    for passage in record.get('passages', []):
        findings = []
        for finding in financial_candidates(passage):
            if finding['evidence_id'] not in seen:
                supported = [item for item in passage.get('llm', {}).get('result', {}).get('financial_findings', [])
                             if item['amount_text'] == finding['amount_text']
                             and item['evidence_quote'] in finding['evidence_quote']]
                if len(supported) == 1:
                    finding['llm_category'] = supported[0]['category']
                    finding['accounting_location'] = supported[0]['accounting_location']
                    finding['amount_reporting_period'] = supported[0]['period_text']
                findings.append(finding)
                seen.add(finding['evidence_id'])
        passage['financial_candidates'] = findings
        count += len(findings)
    fraud_mentioned = any(FRAUD.search(p['text']) for p in record.get('passages', []))
    record['financial_candidate_count'] = count
    record['financial_discovery_status'] = (
        'incomplete_scan' if record.get('status') != 'extracted_needs_review' else
        'candidate_amounts_found' if count else
        'fraud_discussion_no_candidate_amount' if fraud_mentioned else 'no_fraud_terms_found')
    return record


def safe_row(row):
    return {k: "'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@'))
            else v for k, v in row.items()}


def export_financial_reports(path):
    """Latest attempt per filing/scope/version; never sum financial amounts."""
    latest = {}
    with path.open(encoding='utf-8') as source:
        for line in source:
            record = json.loads(line)
            if record.get('scan_version') != VERSION:
                continue
            filing = record.get('filing', {})
            key = (filing.get('cik', record.get('cik')), filing.get('accession'),
                   filing.get('local_html'), record.get('scan_scope'), record.get('focus'))
            latest[key] = record
    base = ['company', 'cik', 'sic', 'form', 'filing_date', 'report_date', 'accession']
    detail = ['evidence_id', 'amount_text', 'normalized_number', 'currency', 'currency_marker',
              'category_candidate', 'statement_basis', 'association', 'evidence_quote',
              'source_url', 'accounting_location', 'amount_reporting_period', 'review_status', 'llm_category',
              'amount_xbrl_tags', 'numeric_xbrl_tags', 'passage_xbrl_tags', 'scan_status']
    amounts_path = path.with_name(path.stem + '_amounts.csv')
    coverage_path = path.with_name(path.stem + '_coverage.csv')
    with amounts_path.open('w', newline='', encoding='utf-8-sig') as amounts, \
         coverage_path.open('w', newline='', encoding='utf-8-sig') as coverage:
        aw = csv.DictWriter(amounts, fieldnames=base + detail)
        cw = csv.DictWriter(coverage, fieldnames=base + ['scan_scope', 'status', 'financial_discovery_status',
                                                       'candidate_count', 'error'])
        aw.writeheader()
        cw.writeheader()
        for record in latest.values():
            filing = record.get('filing', {})
            row = {key: filing.get(key, '') for key in base}
            row['cik'] = filing.get('cik', record.get('cik', ''))
            cw.writerow(safe_row(dict(row, scan_scope=record.get('scan_scope', ''),
                                     status=record.get('status', ''),
                                     financial_discovery_status=record.get('financial_discovery_status', 'not_analyzed'),
                                     candidate_count=record.get('financial_candidate_count', ''),
                                     error=record.get('error', ''))))
            for passage in record.get('passages', []):
                for finding in passage.get('financial_candidates', []):
                    evidence = {key: finding.get(key, '') for key in detail}
                    evidence['scan_status'] = record.get('status', '')
                    tags = finding.get('amount_xbrl_tags', [])
                    evidence['amount_xbrl_tags'] = '; '.join(sorted({f['name'] for f in tags}))
                    evidence['numeric_xbrl_tags'] = '; '.join(sorted({f['name'] for f in tags
                                                                 if f.get('element') == 'ix:nonfraction'}))
                    evidence['passage_xbrl_tags'] = '; '.join(sorted({f['name'] for f in passage.get('tags', [])}))
                    aw.writerow(safe_row(dict(row, **evidence)))
    return amounts_path, coverage_path


def load_ciks(path):
    """A plain CIK per line, or a CSV with a 'cik' column; no inferred membership."""
    text = Path(path).read_text(encoding='utf-8-sig')
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if not lines:
        raise ValueError('CIK file is empty')
    if 'cik' in [name.strip().lower() for name in lines[0].split(',')]:
        reader = csv.DictReader(lines)
        column = next(name for name in reader.fieldnames if name.strip().lower() == 'cik')
        values = [row[column].strip() for row in reader]
    else:
        values = lines
    if any(not value.isdigit() or len(value) > 10 for value in values):
        raise ValueError('Use numeric CIKs, one per line, or a CSV with a cik column')
    return list(dict.fromkeys(str(int(value)) for value in values))
