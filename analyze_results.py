"""Reproduce the analysis of the uploaded Debian run. Does not download filings."""
import csv
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re

os.environ.setdefault('MPLCONFIGDIR', '/tmp/fraud-discovery-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'results' / '2026-11-21_003915_094872'
OUT = ROOT / 'analysis' / 'debian_2026-11-21'


def load(name):
    with (SOURCE / name).open(encoding='utf-8-sig', newline='') as source:
        return list(csv.DictReader(source))


def write(name, rows):
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def material(row):
    return '1.05' in set(re.findall(r'\b[1-9]\.\d{2}\b', row['declared_items']))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    coverage, filings, findings = load('coverage.csv'), load('filings.csv'), load('findings.csv')
    success = [r for r in filings if r['status'] == 'scanned']
    errors = [r for r in filings if r['status'] != 'scanned']
    complete = {r['cik'] for r in coverage if r['status'] == 'complete'}
    fraud = [r for r in success if r['fraud_match'] == 'True']
    cyber = [r for r in success if r['cyber_match'] == 'True']
    both = [r for r in success if r['fraud_match'] == r['cyber_match'] == 'True']
    items = [r for r in success if material(r)]
    assert len(coverage) == len({r['cik'] for r in coverage}) == 500
    assert len(filings) == len({(r['cik'], r['accession']) for r in filings})
    assert sum(int(r['scanned_filings']) for r in coverage) == len(success)
    assert sum(int(r['failed_filings']) for r in coverage) == len(errors)
    assert sum(int(r['eligible_filings']) for r in coverage) == len(filings)
    sectors = []
    for sector in sorted({r['sector'] for r in coverage}):
        companies = [r for r in coverage if r['sector'] == sector]
        valid = [r for r in success if r['sector'] == sector]
        ff = [r for r in valid if r['fraud_match'] == 'True']
        cc = [r for r in valid if r['cyber_match'] == 'True']
        ii = [r for r in valid if material(r)]
        full = {r['cik'] for r in companies if r['cik'] in complete}
        fc = len({r['cik'] for r in ff if r['cik'] in full})
        cy = len({r['cik'] for r in cc if r['cik'] in full})
        sectors.append({'sector': sector, 'constituents': len(companies), 'complete_companies': len(full),
                        'coverage_percent': round(100 * len(full) / len(companies), 2),
                        'scanned_filings': len(valid), 'fraud_keyword_filings': len(ff),
                        'cyber_keyword_filings': len(cc), 'item_1_05_filings': len(ii),
                        'item_1_05_companies': len({r['cik'] for r in ii}),
                        'fraud_per_1000_filings': round(1000 * len(ff) / len(valid), 3),
                        'cyber_per_1000_filings': round(1000 * len(cc) / len(valid), 3),
                        'complete_companies_with_fraud_match': fc,
                        'complete_companies_with_cyber_match': cy,
                        'fraud_percent_complete_companies': round(100 * fc / len(full), 2),
                        'cyber_percent_complete_companies': round(100 * cy / len(full), 2)})
    write('sector_comparison.csv', sectors)
    write('item_1_05_filings.csv', [{k: r[k] for k in ['ticker', 'company', 'sector', 'cik', 'form', 'filing_date', 'accession', 'source_url', 'declared_items']} for r in items])
    write('failed_filings.csv', errors)
    write('top_keyword_companies.csv', [
        {'category': category, 'ticker': ticker, 'matching_filings': count}
        for category, rows in [('fraud', fraud), ('cybersecurity', cyber)]
        for ticker, count in Counter(r['ticker'] for r in rows).most_common(20)])
    phrase = 'losses related to fraud, theft, misappropriation or violence'
    repeated = {r['accession'] for r in findings if r['ticker'] == 'FITB' and phrase in r['text'].lower()}
    metrics = {'run_label': 'Debian', 'run_folder': SOURCE.name, 'collector_reference_commit': '6695fc335577b996a93995002e7f33dad267a897',
               'collector_revision_note': 'Repository version preceding upload; the scan did not record its own Git revision.',
               'companies': len(coverage), 'complete_companies': len(complete),
               'partial_companies': len(coverage) - len(complete), 'attempted_filings': len(filings),
               'successful_filings': len(success), 'failed_filings': len(errors),
               'file_success_percent': round(100 * len(success) / len(filings), 3),
               'fraud_keyword_filings': len(fraud), 'fraud_keyword_companies_all_coverage': len({r['cik'] for r in fraud}),
               'cyber_keyword_filings': len(cyber), 'cyber_keyword_companies_all_coverage': len({r['cik'] for r in cyber}),
               'both_keyword_categories_filings': len(both),
               'either_keyword_category_filings': len(fraud) + len(cyber) - len(both),
               'evidence_passages': len(findings), 'corrected_item_1_05_filings': len(items),
               'corrected_item_1_05_companies': len({r['cik'] for r in items}),
               'old_item_106_true_count': sum(r['item_106'] == 'True' for r in success),
               'fifth_third_fraud_keyword_filings': sum(r['ticker'] == 'FITB' for r in fraud),
               'fifth_third_filings_with_identical_risk_phrase': len(repeated),
               'firstenergy_cyber_keyword_filings': sum(r['ticker'] == 'FE' for r in cyber),
               'xcel_cyber_keyword_filings': sum(r['ticker'] == 'XEL' for r in cyber),
               'successful_forms': dict(Counter(r['form'] for r in success)),
               'errors': dict(Counter(r['error'] for r in errors)),
               'filing_date_min': min(r['filing_date'] for r in success),
               'filing_date_max': max(r['filing_date'] for r in success),
               'source_sha256': {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest()
                                 for name in ['coverage.csv', 'filings.csv', 'findings.csv', 'sector_summary.csv', 'DISCOVERY.md']}}
    (OUT / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    def save(fig, name):
        fig.savefig(OUT / (name + '.png'), dpi=180, bbox_inches='tight')
        fig.savefig(OUT / (name + '.svg'), bbox_inches='tight')
        plt.close(fig)
    ordered = sorted(sectors, key=lambda r: r['fraud_per_1000_filings'], reverse=True)
    y = np.arange(len(ordered))
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.barh(y - .19, [r['fraud_per_1000_filings'] for r in ordered], height=.36, label='Fraud-related vocabulary', color='#be5b31')
    ax.barh(y + .19, [r['cyber_per_1000_filings'] for r in ordered], height=.36, label='Cybersecurity vocabulary', color='#276e9e')
    ax.set_yticks(y, [r['sector'] for r in ordered]); ax.invert_yaxis()
    ax.set_xlabel('Matching filings per 1,000 successfully scanned 8-K / 8-K/A documents')
    ax.set_title('Debian discovery: fraud and cybersecurity disclosure language', loc='left', fontweight='bold')
    ax.legend(loc='lower right'); ax.grid(axis='x', alpha=.15)
    fig.text(.02, -.015, '2020–2026 snapshot panel; keyword matches include risks and boilerplate. Categories overlap. Not incident or loss rates.', fontsize=9)
    save(fig, '01_keyword_filing_rates')
    ordered = sorted(sectors, key=lambda r: r['fraud_percent_complete_companies'], reverse=True)
    y = np.arange(len(ordered))
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.barh(y - .19, [r['fraud_percent_complete_companies'] for r in ordered], height=.36, label='Fraud-related vocabulary', color='#be5b31')
    ax.barh(y + .19, [r['cyber_percent_complete_companies'] for r in ordered], height=.36, label='Cybersecurity vocabulary', color='#276e9e')
    ax.set_yticks(y, [f'{r["sector"]} (n={r["complete_companies"]})' for r in ordered]); ax.invert_yaxis()
    ax.set_xlim(0, 100); ax.set_xlabel('Percent of fully scanned companies with at least one matching filing')
    ax.set_title('Company-level disclosure prevalence: fully scanned subset only', loc='left', fontweight='bold')
    ax.legend(loc='lower right'); ax.grid(axis='x', alpha=.15)
    fig.text(.02, -.015, '435 fully scanned companies. Partial companies excluded from numerator and denominator. Not fraud incidence.', fontsize=9)
    save(fig, '02_company_disclosure_rates')
    ordered = sorted(sectors, key=lambda r: r['coverage_percent'])
    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(ordered))
    ax.barh(y, [r['coverage_percent'] for r in ordered], color='#478c78')
    for i, r in enumerate(ordered): ax.text(r['coverage_percent'] + .5, i, f'{r["complete_companies"]}/{r["constituents"]}', va='center')
    ax.set_yticks(y, [r['sector'] for r in ordered]); ax.invert_yaxis(); ax.set_xlim(0, 110)
    ax.set_xlabel('Percent of companies with every identified filing successfully scanned')
    ax.set_title('Coverage: 435 complete companies; 65 partial', loc='left', fontweight='bold')
    fig.text(.02, -.015, '44,845 of 44,928 attempted filing documents succeeded (99.815%). A single failure makes a company partial.', fontsize=9)
    save(fig, '03_coverage')
    ordered = sorted([r for r in sectors if r['item_1_05_filings']], key=lambda r: r['item_1_05_filings'], reverse=True)
    y = np.arange(len(ordered))
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(y - .19, [r['item_1_05_filings'] for r in ordered], height=.36, color='#6b5a9a', label='Filings, including amendments')
    ax.barh(y + .19, [r['item_1_05_companies'] for r in ordered], height=.36, color='#478c78', label='Distinct companies')
    ax.set_yticks(y, [r['sector'] for r in ordered]); ax.invert_yaxis()
    ax.set_xlabel('Count in successfully scanned documents'); ax.set_xticks(range(0, 12, 2))
    ax.set_title('Corrected Item 1.05 result: 21 filings from 14 companies', loc='left', fontweight='bold')
    ax.legend(loc='lower right')
    fig.text(.02, -.015, 'Recovered from SEC-declared item metadata. Item 1.05 is cybersecurity, not proof of fraud. Amendments are not new incidents.', fontsize=9)
    save(fig, '04_item_1_05')
    print(json.dumps({k: v for k, v in metrics.items() if k != 'source_sha256'}, indent=2))


if __name__ == '__main__':
    main()
