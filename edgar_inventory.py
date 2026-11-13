"""Populate a CSV of financial-services filings using SEC metadata only."""

import argparse
import csv
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# A small starting sample, not a complete financial-services universe.
SAMPLE_CIKS = ['19617', '70858', '72971', '831001', '886982', '895421']
FIELDS = ['company', 'cik', 'sic', 'sic_description', 'form', 'filing_date',
          'report_date', 'accession', 'primary_document', 'edgar_url']


def fetch_submissions_json(filename, user_agent):
    if '/' in filename or '\\' in filename or not filename.endswith('.json'):
        raise ValueError('Invalid SEC submissions filename')
    url = f'https://data.sec.gov/submissions/{filename}'
    request = Request(url, headers={'User-Agent': user_agent,
                                   'Accept': 'application/json'})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_company(cik, user_agent):
    return fetch_submissions_json(f'CIK{int(cik):010d}.json', user_agent)


def company_history(cik, user_agent, since, until):
    """Include older submissions files whose date ranges overlap the request."""
    company = fetch_company(cik, user_agent)
    merged = dict(company.get('filings', {}).get('recent', {}))
    for archive in company.get('filings', {}).get('files', []):
        if archive.get('filingTo', '9999-12-31') < since:
            continue
        if archive.get('filingFrom', '0000-01-01') > until:
            continue
        time.sleep(0.25)
        older = fetch_submissions_json(archive['name'], user_agent)
        # SEC historical files contain the filing arrays directly.
        keys = set(merged) | set(older)
        previous_count = len(merged.get('form', []))
        older_count = len(older.get('form', []))
        merged = {key: merged.get(key, [''] * previous_count)
                  + older.get(key, [''] * older_count) for key in keys}
    company = dict(company)
    company['filings'] = {'recent': merged}
    return company


def filing_rows(company, forms, since, sic_min=6000, sic_max=6799):
    """Filter the recent metadata returned by the submissions endpoint."""
    try:
        sic = int(company.get('sic', ''))
    except (TypeError, ValueError):
        return
    if not sic_min <= sic <= sic_max:
        return
    recent = company.get('filings', {}).get('recent', {})
    for index, form in enumerate(recent.get('form', [])):
        def value(key):
            values = recent.get(key, [])
            return values[index] if index < len(values) else ''

        date = value('filingDate')
        if form not in forms or date < since:
            continue
        accession = value('accessionNumber')
        cik = str(int(company['cik']))
        yield {
            'company': company.get('name', ''), 'cik': cik, 'sic': sic,
            'sic_description': company.get('sicDescription', ''),
            'form': form, 'filing_date': date, 'report_date': value('reportDate'),
            'accession': accession, 'primary_document': value('primaryDocument'),
            'edgar_url': f'https://www.sec.gov/Archives/edgar/data/{cik}/'
                         f'{accession.replace("-", "")}/{accession}-index.html',
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ciks', nargs='+', default=SAMPLE_CIKS,
                        help='Company CIKs; defaults to six large banks.')
    parser.add_argument('--forms', nargs='+', default=['10-K', '8-K'])
    parser.add_argument('--since', default='2023-01-01')
    parser.add_argument('--sic-min', type=int, default=6000)
    parser.add_argument('--sic-max', type=int, default=6799)
    parser.add_argument('--output', type=Path, default=Path('data/filings.csv'))
    args = parser.parse_args()
    try:
        time.strptime(args.since, '%Y-%m-%d')
        if args.sic_min > args.sic_max or any(not x.isdigit() for x in args.ciks):
            raise ValueError()
    except ValueError:
        parser.error('Use numeric CIKs, a YYYY-MM-DD date, and an ordered SIC range.')
    user_agent = os.environ.get('SEC_USER_AGENT', '').strip()
    if not user_agent:
        parser.error('Set SEC_USER_AGENT to your project name and contact email.')

    rows, failures = [], []
    for cik in dict.fromkeys(args.ciks):
        try:
            company = fetch_company(cik, user_agent)
            matches = list(filing_rows(company, set(args.forms), args.since,
                                       args.sic_min, args.sic_max))
            rows.extend(matches)
            print(f'{company.get("name", cik)}: {len(matches)} filings')
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            failures.append(cik)
            print(f'CIK {cik}: {error}', file=sys.stderr)
        # Conservative sequential requests, including after failures.
        time.sleep(0.25)
    if failures:
        print('Incomplete collection; existing output was not replaced. '
              'Check SEC access and retry.', file=sys.stderr)
        return 1
    rows.sort(key=lambda row: (row['filing_date'], row['cik']), reverse=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Saved {len(rows)} filing records to {args.output}')
    print('Scope: recent SEC metadata only; this is not an exhaustive history '
          'or a fraud search. Filing documents were not downloaded.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
