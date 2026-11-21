"""Scan S&P 500 annual, quarterly, and current disclosures. No arguments or API key."""
import csv
from datetime import date, datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from disclosure_evidence import amount_rows, describe, financial_windows, write_company_years

ROOT = Path(__file__).resolve().parent
START_DATE = '2020-01-01'
USER_AGENT = 'FraudDiscovery andrew@johnson.vet'
FORMS = {'8-K', '8-K/A', '10-K', '10-K/A', '10-Q', '10-Q/A'}
PATTERNS = {
    'fraud': re.compile(r'\b(?:fraud\w*|scams?|embezzl\w*|misappropriat\w*|'
                       r'identity theft|account takeovers?|false claims|'
                       r'unauthori[sz]ed transactions?|business e[- ]?mail compromise)\b', re.I),
    'cybersecurity': re.compile(r'\b(?:cyber\w*|ransomware|phishing|data breaches?|'
                               r'security (?:breaches?|incidents?)|network intrusion|'
                               r'unauthori[sz]ed access|social engineering)\b', re.I),
}
ITEM = re.compile(r'\bItem\s+([1-9]\.\d{2}|\d{1,2}[A-C]?)\b', re.I)


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'ix:header', 'ix:hidden'}:
            self.hidden += 1
        if not self.hidden and tag in {'p', 'div', 'br', 'td', 'tr', 'li', 'h1', 'h2', 'h3'}:
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'ix:header', 'ix:hidden'}:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in {'p', 'div', 'td', 'tr', 'li', 'h1', 'h2', 'h3'}:
            self.parts.append(' ')

    def handle_data(self, text):
        if not self.hidden:
            self.parts.append(text)


def extract_text(html):
    parser = VisibleText()
    parser.feed(html)
    return re.sub(r'\s+', ' ', ''.join(parser.parts)).strip()


class SEC:
    def __init__(self):
        self.previous_request = 0

    def read(self, url):
        # Brief retries address the transient failures observed in the Debian run.
        for attempt in range(3):
            wait = 0.5 - (time.monotonic() - self.previous_request)
            if wait > 0:
                time.sleep(wait)
            self.previous_request = time.monotonic()
            try:
                with urlopen(Request(url, headers={'User-Agent': USER_AGENT}), timeout=40) as response:
                    return response.read()
            except (HTTPError, URLError, TimeoutError) as error:
                transient = (isinstance(error, HTTPError) and error.code in {502, 503, 504}
                             or isinstance(error, URLError) and 'Tunnel connection failed' not in str(error)
                             or isinstance(error, TimeoutError))
                if not transient or attempt == 2:
                    raise
                time.sleep(attempt + 1)

    def json(self, url):
        return json.loads(self.read(url))


def get_filings(sec, cik, until):
    company = sec.json(f'https://data.sec.gov/submissions/CIK{int(cik):010d}.json')
    arrays = [company.get('filings', {}).get('recent', {})]
    for archive in company.get('filings', {}).get('files', []):
        if archive.get('filingTo', '9999-12-31') < START_DATE:
            continue
        if archive.get('filingFrom', '0000-01-01') > until:
            continue
        name = archive['name']
        arrays.append(sec.json('https://data.sec.gov/submissions/' + quote(name, safe='')))
    found = {}
    for block in arrays:
        for i, form in enumerate(block.get('form', [])):
            def field(key):
                values = block.get(key, [])
                return values[i] if i < len(values) else ''
            if form not in FORMS or not START_DATE <= field('filingDate') <= until:
                continue
            accession = field('accessionNumber')
            if accession in found:
                continue
            document = field('primaryDocument')
            found[accession] = {
                'accession': accession, 'form': form, 'filing_date': field('filingDate'),
                'report_date': field('reportDate'),
                'declared_items': field('items'),
                'source_url': f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/'
                              f'{accession.replace("-", "")}/{quote(document, safe="/")}',
            }
    return sorted(found.values(), key=lambda row: row['filing_date'], reverse=True)


def inspect(text, declared_items='', form='8-K'):
    headings = list(ITEM.finditer(text))
    declared = set(re.findall(r'\b[1-9]\.\d{2}\b', declared_items))
    items = set(declared)
    items.update(match.group(1) for match in headings)
    matches = [(match.start(), match.end()) for pattern in PATTERNS.values()
               for match in pattern.finditer(text)]
    # Capture a material cybersecurity disclosure even if its wording evades keywords.
    current_report = form in {'8-K', '8-K/A'}
    matches.extend((match.start(), match.end()) for match in headings
                   if current_report and match.group(1) == '1.05')
    if current_report and '1.05' in items and not matches:
        matches.append((0, min(1000, len(text))))
    windows = []
    for start, end in sorted(matches):
        left, right = max(0, start - 1500), min(len(text), end + 1500)
        windows.append([left, right])
    windows.extend([list(window) for window in financial_windows(text, PATTERNS)])
    merged = []
    for left, right in sorted(windows):
        if merged and left <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], right)
        else:
            merged.append([left, right])
    passages = []
    for left, right in merged:
        for start in range(left, right, 5800):
            end = min(start + 6000, right)
            snippet = text[start:end]
            anchors = [start + match.start() for pattern in PATTERNS.values()
                       for match in pattern.finditer(snippet)]
            anchor = min(anchors) if anchors else start
            preceding = [m.group(1) for m in headings if m.start() <= anchor]
            passages.append({'text': snippet, 'offset': start,
                             'preceding_item_candidate': preceding[-1] if preceding else '',
                             'categories': '; '.join(name for name, pattern in PATTERNS.items()
                                                     if pattern.search(snippet))})
    material = current_report and ('1.05' in declared if declared else bool(re.search(
        r'\bItem\s+1\.05[. :]*Material\s+Cybersecurity\s+Incidents?', text, re.I)))
    return {'items': '; '.join(sorted(items)), 'item_1_05': material,
            'fraud_match': bool(PATTERNS['fraud'].search(text)),
            'cyber_match': bool(PATTERNS['cybersecurity'].search(text)), 'passages': passages}


def safe(row):
    return {key: "'" + value if isinstance(value, str) and
            value.lstrip().startswith(('=', '+', '-', '@')) else value for key, value in row.items()}


def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8-sig') as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(safe(row) for row in rows)


def summarize(coverage):
    summary = []
    for sector in sorted({row['sector'] for row in coverage}):
        rows = [r for r in coverage if r['sector'] == sector]
        complete = [r for r in rows if r['status'] == 'complete']
        relevant = sum(r['fraud_filings'] > 0 or r['cyber_filings'] > 0 or r['item_1_05_filings'] > 0
                       for r in complete)
        summary.append({
            'sector': sector, 'constituents': len(rows), 'complete_companies': len(complete),
            'incomplete_companies': len(rows) - len(complete),
            'scanned_filings': sum(r['scanned_filings'] for r in rows),
            'fraud_keyword_filings': sum(r['fraud_filings'] for r in rows),
            'cyber_keyword_filings': sum(r['cyber_filings'] for r in rows),
            'item_1_05_filings': sum(r['item_1_05_filings'] for r in rows),
            'complete_companies_with_relevant_disclosures': relevant,
            'relevant_percent_of_complete_companies': round(100 * relevant / len(complete), 1) if complete else '',
        })
    return summary


def write_analysis(folder, coverage, until, stopped):
    summary = summarize(coverage)
    write_csv(folder / 'coverage.csv', coverage, list(coverage[0]))
    write_csv(folder / 'sector_summary.csv', summary, list(summary[0]))
    complete = sum(row['status'] == 'complete' for row in coverage)
    scanned = sum(row['scanned_filings'] for row in coverage)
    table = '\n'.join(f'| {r["sector"]} | {r["complete_companies"]}/{r["constituents"]} | '
                      f'{r["scanned_filings"]} | {r["fraud_keyword_filings"]} | '
                      f'{r["cyber_keyword_filings"]} | {r["item_1_05_filings"]} | '
                      f'{r["relevant_percent_of_complete_companies"] if r["relevant_percent_of_complete_companies"] != "" else "Not available"} |' for r in summary)
    report = f'''# S&P 500 fraud disclosure discovery

Period: {START_DATE} through {until} (filing dates). Status: {"STOPPED / INCOMPLETE" if stopped else "FINISHED WITH ERRORS" if complete < len(coverage) else "COMPLETE"}.
Companies completely scanned: {complete}/{len(coverage)}. Primary filing documents scanned: {scanned}.

{('Collection stopped: ' + stopped) if stopped else ''}
{'**No filing text was collected; there are no research findings.**' if not scanned else ''}

| Sector | Complete/constituents | Scanned documents | Fraud-word filings | Cyber-word filings | Item 1.05 filings | Relevant % of complete companies |
|---|---:|---:|---:|---:|---:|---:|
{table}

## What the program did

Read the bundled 500-company snapshot, retrieve recent and historical SEC metadata,
scan all available 10-K, 10-Q, 8-K and amendment primary documents in the period, identify item
numbers and fraud/cybersecurity vocabulary, and retain source excerpts. No LLM,
API key, images, raw filing downloads, or cache. Other than the bundled company
list, only result CSVs and this report are saved. Reruns start a new scan.

Item 1.05 concerns material cybersecurity incidents. Regulation S-K Item 106 is a separate annual disclosure rule.
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
no eligible filings is included in the company denominator. An unscanned sector is
unknown, not zero fraud. Do not rank sectors until coverage is comparable.

The company list is a third-party snapshot retrieved November 20, 2026, sourced
from Wikipedia via datasets/s-and-p-500-companies. It is not independently verified
official membership or historical membership. Share classes with the same CIK are
scanned once. Applying the snapshot to 2020 onward creates a fixed-company panel.
Item 1.05 reporting began in December 2023, so comparisons across that date reflect
changes in disclosure requirements as well as possible underlying events.

## Additional evidence and comparison tables

`company_year.csv` groups coverage and disclosure flags by company and filing year
(not fiscal year or incident year). Annual, quarterly, and current reports are
counted separately. Unknown metadata, incomplete scans, and no-filings years are
not zero fraud. Restrict comparisons to comparable covered periods and form types.

`findings.csv` includes longer excerpts, exact-text repetition fingerprints,
and separate risk/event/allegation/contract word flags. These are lexical review
aids, not validated semantic classes. Repeated text does not establish repeated
events, and changed wording does not establish a new event. Same-text flags compare
within a company and retain numbers; different amounts are not silently merged.

`amount_candidates.csv` records monetary expressions in retained context. Cost
paragraphs referring to an incident can be retained even far from the original
keyword. Every amount is unreviewed: proximity does not establish fraud attribution,
currency, realized loss, or the reporting period. There is no automatic sum.

These additions support examining associations between sector, filing year, type
of disclosure, and reported financial-impact evidence. They do not measure the
causal effect of fraud on stock prices, S&P 500 returns, or criminal revenue.

## Next research step

Review findings.csv to separate actual incidents from risks and corporate
misconduct from victimization. Deduplicate related filings into events. Then
compare sector disclosure rates and, where explicitly stated, financial impacts.
If quantities are sparse, study the specificity of disclosures rather than
claiming to measure total fraud costs. No automatic amount summation is performed.
'''
    (folder / 'DISCOVERY.md').write_text(report, encoding='utf-8')


def access_block(error):
    return (isinstance(error, HTTPError) and error.code in {401, 403, 429}
            or isinstance(error, URLError) and 'Tunnel connection failed' in str(error))


def main():
    source = ROOT / 'companies.csv'
    manifest = json.loads((ROOT / 'companies_source.json').read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest() != manifest['csv_sha256']:
        raise ValueError('Company list does not match its source manifest')
    with source.open(encoding='utf-8') as company_file:
        companies = list(csv.DictReader(company_file))
    until = date.today().isoformat()
    folder = ROOT / 'results' / datetime.now().strftime('%Y-%m-%d_%H%M%S_%f')
    folder.mkdir(parents=True)
    coverage = [dict(company, status='not_started', eligible_filings='', scanned_filings=0,
                     failed_filings=0, fraud_filings=0, cyber_filings=0, item_1_05_filings=0, error='')
                for company in companies]
    sec = SEC()
    stopped = ''
    eligible_years = {}
    seen_passages = {}
    base = ['cik', 'ticker', 'company', 'sector', 'accession', 'form', 'filing_date', 'report_date', 'source_url']
    filing_fields = base + ['declared_items', 'found_items', 'fraud_match', 'cyber_match', 'item_1_05', 'status', 'error']
    finding_fields = base + ['declared_items', 'found_items', 'preceding_item_candidate', 'categories',
                             'risk_language', 'event_language', 'allegation_language', 'contract_language',
                             'financial_terms', 'evidence_fingerprint', 'same_text_other_filing',
                             'repeat_reference_accession', 'review_status', 'offset', 'text']
    amount_fields = base + ['amount_text', 'amount_offset', 'association', 'financial_terms', 'review_status', 'text']
    print(f'Scanning {len(companies)} companies, 10-K/10-Q/8-K and amendments, {START_DATE}–{until}.')
    print('SEC contact: andrew@johnson.vet. No arguments or API keys. This can take hours.')
    try:
        with (folder / 'filings.csv').open('w', newline='', encoding='utf-8-sig') as filing_file, \
             (folder / 'findings.csv').open('w', newline='', encoding='utf-8-sig') as finding_file, \
             (folder / 'amount_candidates.csv').open('w', newline='', encoding='utf-8-sig') as amount_file:
            fw = csv.DictWriter(filing_file, fieldnames=filing_fields)
            ew = csv.DictWriter(finding_file, fieldnames=finding_fields)
            aw = csv.DictWriter(amount_file, fieldnames=amount_fields)
            fw.writeheader()
            ew.writeheader()
            aw.writeheader()
            for index, row in enumerate(coverage, 1):
                company = {key: row[key] for key in ('cik', 'ticker', 'company', 'sector')}
                print(f'[{index}/{len(companies)}] {row["ticker"]}: metadata... ', flush=True)
                try:
                    filings = get_filings(sec, row['cik'], until)
                    row['eligible_filings'] = len(filings)
                    for year in range(int(START_DATE[:4]), int(until[:4]) + 1):
                        eligible_years[(row['cik'], year)] = 0
                    for filing in filings:
                        eligible_years[(row['cik'], int(filing['filing_date'][:4]))] += 1
                except Exception as error:
                    row.update(status='metadata_error', error=str(error))
                    if access_block(error):
                        stopped = str(error)
                        break
                    continue
                row['status'] = 'scanning'
                for filing_index, filing in enumerate(filings, 1):
                    result = {**company, **filing}
                    try:
                        text = extract_text(sec.read(filing['source_url']).decode('utf-8', errors='replace'))
                        if not text:
                            raise ValueError('No readable primary-document text')
                        analysis = inspect(text, filing['declared_items'], filing['form'])
                        result.update(found_items=analysis['items'], fraud_match=analysis['fraud_match'],
                                      cyber_match=analysis['cyber_match'], item_1_05=analysis['item_1_05'],
                                      status='scanned', error='')
                        row['scanned_filings'] += 1
                        row['fraud_filings'] += int(analysis['fraud_match'])
                        row['cyber_filings'] += int(analysis['cyber_match'])
                        row['item_1_05_filings'] += int(analysis['item_1_05'])
                        amount_seen = set()
                        for passage in analysis['passages']:
                            passage.update(describe(passage['text']))
                            key = (row['cik'], passage['evidence_fingerprint'])
                            reference = seen_passages.setdefault(key, filing['accession'])
                            passage['same_text_other_filing'] = reference != filing['accession']
                            passage['repeat_reference_accession'] = reference if reference != filing['accession'] else ''
                            ew.writerow(safe({key: result.get(key, passage.get(key, '')) for key in finding_fields}))
                            for amount in amount_rows(passage):
                                if amount['amount_offset'] in amount_seen:
                                    continue
                                amount_seen.add(amount['amount_offset'])
                                aw.writerow(safe({key: result.get(key, amount.get(key, passage.get(key, '')))
                                                  for key in amount_fields}))
                    except Exception as error:
                        row['failed_filings'] += 1
                        result.update(status='error', error=str(error))
                        row['error'] = str(error)
                        if access_block(error):
                            stopped = str(error)
                    fw.writerow(safe({key: result.get(key, '') for key in filing_fields}))
                    filing_file.flush()
                    finding_file.flush()
                    amount_file.flush()
                    if filing_index % 25 == 0:
                        print(f'  {filing_index}/{len(filings)} documents attempted', flush=True)
                    if stopped:
                        break
                row['status'] = 'partial' if stopped or row['failed_filings'] else 'complete'
                print(f'  {row["scanned_filings"]}/{row["eligible_filings"]} filing documents scanned', flush=True)
                write_analysis(folder, coverage, until, stopped)
                if stopped:
                    break
    except KeyboardInterrupt:
        stopped = 'Stopped by user; results are partial.'
        for row in coverage:
            if row['status'] == 'scanning':
                row.update(status='partial', error=stopped)
    finally:
        write_analysis(folder, coverage, until, stopped)
        write_company_years(folder, coverage, eligible_years, int(START_DATE[:4]), int(until[:4]))
    print('Report:', folder / 'DISCOVERY.md')
    if stopped:
        print('Collection stopped:', stopped)
    return int(bool(stopped) or any(row['status'] != 'complete' for row in coverage))


if __name__ == '__main__':
    raise SystemExit(main())
