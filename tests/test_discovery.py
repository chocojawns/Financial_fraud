import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

import discovery


class DiscoveryTests(unittest.TestCase):
    def test_text_and_full_document_matches(self):
        text = discovery.extract_text('<style>fraud</style><p>Item 8.01 Other Events</p>'
                                      '<p>We identified an account takeover and ransomware.</p>'
                                      '<ix:hidden>hidden data</ix:hidden>')
        self.assertNotIn('hidden data', text)
        result = discovery.inspect(text, '8.01')
        self.assertTrue(result['fraud_match'])
        self.assertTrue(result['cyber_match'])
        self.assertFalse(result['item_1_05'])
        self.assertIn('account takeover', result['passages'][0]['text'])

    def test_other_item_number_alone_is_not_a_fraud_match(self):
        result = discovery.inspect('Item 4.02 Financial statements should not be relied upon.', '4.02')
        self.assertFalse(result['fraud_match'])
        self.assertFalse(result['cyber_match'])
        self.assertEqual(result['passages'], [])

    def test_material_item_and_cross_reference_are_distinct(self):
        self.assertTrue(discovery.inspect('See attached notice.', '1.05')['item_1_05'])
        self.assertTrue(discovery.inspect('Item 1.05. Material Cybersecurity Incidents')['item_1_05'])
        self.assertTrue(discovery.inspect('Item 1.05 Material Cybersecurity Incident')['item_1_05'])
        self.assertFalse(discovery.inspect('Item 1.06 Unrelated item', '1.06')['item_1_05'])
        self.assertFalse(discovery.inspect('Item 8.01 We refer to Item 1.05.', '8.01')['item_1_05'])

    def test_metadata_history_forms_dates_and_deduplication(self):
        recent = {'form': ['8-K', '10-K', '8-K/A'],
                  'filingDate': ['2026-01-01'] * 3,
                  'accessionNumber': ['a', 'b', 'c'],
                  'primaryDocument': ['a.htm', 'b.htm', 'c.htm'], 'items': ['1.05', '', '8.01']}
        archive = {'form': ['8-K', '8-K', '8-K'],
                   'filingDate': ['2026-01-01', '2020-05-01', '2019-01-01'],
                   'accessionNumber': ['a', 'd', 'e'], 'primaryDocument': ['a.htm', 'd.htm', 'e.htm']}
        class FakeSEC:
            def json(self, url):
                if url.endswith('old.json'):
                    return archive
                return {'filings': {'recent': recent, 'files': [
                    {'name': 'old.json', 'filingFrom': '2019-01-01', 'filingTo': '2026-01-01'}]}}
        rows = discovery.get_filings(FakeSEC(), '19617', '2026-11-20')
        self.assertEqual({r['accession'] for r in rows}, {'a', 'b', 'c', 'd'})
        self.assertEqual(next(r for r in rows if r['accession'] == 'a')['declared_items'], '1.05')
        self.assertTrue(all(r['form'] in discovery.FORMS for r in rows))

    def test_partial_companies_are_excluded_from_percentage(self):
        rows = [dict(sector='Financials', status='complete', scanned_filings=2,
                     fraud_filings=1, cyber_filings=0, item_1_05_filings=0),
                dict(sector='Financials', status='partial', scanned_filings=1,
                     fraud_filings=1, cyber_filings=0, item_1_05_filings=0)]
        result = discovery.summarize(rows)[0]
        self.assertEqual(result['complete_companies'], 1)
        self.assertEqual(result['fraud_keyword_filings'], 2)
        self.assertEqual(result['relevant_percent_of_complete_companies'], 100)
        rows[0]['fraud_filings'] = 0
        self.assertEqual(discovery.summarize(rows)[0]['relevant_percent_of_complete_companies'], 0)
        rows[0]['status'] = 'not_started'
        self.assertEqual(discovery.summarize(rows)[0]['relevant_percent_of_complete_companies'], '')

    def set_up_root(self, root):
        rows = [{'cik': '1', 'ticker': 'ONE', 'company': 'One', 'sector': 'Financials'},
                {'cik': '2', 'ticker': 'TWO', 'company': 'Two', 'sector': 'Industrials'}]
        with (root / 'companies.csv').open('w', newline='') as output:
            writer = csv.DictWriter(output, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        checksum = hashlib.sha256((root / 'companies.csv').read_bytes()).hexdigest()
        (root / 'companies_source.json').write_text(json.dumps({'csv_sha256': checksum}))

    def test_run_saves_results_only_and_compares_sectors(self):
        class FakeSEC:
            def read(self, url):
                return b'<p>Item 1.05 Material Cybersecurity Incidents</p><p>Ransomware affected us.</p>'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.set_up_root(root)
            filing = {'accession': 'a', 'form': '8-K', 'filing_date': '2026-01-01',
                      'source_url': 'https://www.sec.gov/example.htm', 'declared_items': '1.05'}
            with patch.object(discovery, 'ROOT', root), patch.object(discovery, 'SEC', FakeSEC), \
                 patch.object(discovery, 'get_filings', return_value=[filing]), patch('builtins.print'):
                self.assertEqual(discovery.main(), 0)
            result = next((root / 'results').iterdir())
            self.assertEqual({p.name for p in result.iterdir()},
                             {'DISCOVERY.md', 'filings.csv', 'findings.csv', 'coverage.csv',
                              'sector_summary.csv', 'company_year.csv', 'amount_candidates.csv'})
            with (result / 'sector_summary.csv').open(encoding='utf-8-sig') as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(r['relevant_percent_of_complete_companies'] == '100.0' for r in rows))
            with (result / 'company_year.csv').open(encoding='utf-8-sig') as source:
                panel = list(csv.DictReader(source))
            self.assertTrue(all(r['status'] == 'complete' for r in panel if r['filing_year'] == '2026'))
            self.assertTrue(all(r['status'] == 'no_filings_in_window' for r in panel if r['filing_year'] == '2020'))

    def test_blocked_run_keeps_unstarted_companies_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.set_up_root(root)
            with patch.object(discovery, 'ROOT', root), \
                 patch.object(discovery, 'get_filings', side_effect=URLError('Tunnel connection failed: 403 Forbidden')) as fetch, \
                 patch('builtins.print'):
                self.assertEqual(discovery.main(), 1)
            fetch.assert_called_once()
            result = next((root / 'results').iterdir())
            with (result / 'coverage.csv').open(encoding='utf-8-sig') as source:
                rows = list(csv.DictReader(source))
            self.assertEqual([r['status'] for r in rows], ['metadata_error', 'not_started'])
            self.assertIn('no research findings', (result / 'DISCOVERY.md').read_text())
            with (result / 'company_year.csv').open(encoding='utf-8-sig') as source:
                self.assertTrue(all(r['status'] == 'unknown_metadata' and r['eligible_filings'] == ''
                                    for r in csv.DictReader(source)))

    def test_cost_paragraph_far_from_keyword_is_retained(self):
        text = ('Item 1.05 Material Cybersecurity Incident. Fraud monitoring was increased. '
                + 'Unrelated operational discussion. ' * 150
                + 'We estimated expenses of $180 million to $400 million for remediation '
                'and customer reimbursements relating to this Incident.')
        result = discovery.inspect(text, '1.05', '8-K')
        self.assertTrue(any('$180 million' in p['text'] and '$400 million' in p['text']
                            for p in result['passages']))

    def test_annual_report_does_not_count_as_current_incident_item(self):
        result = discovery.inspect('Item 1C Cybersecurity. We reference Item 1.05.', '', '10-K')
        self.assertFalse(result['item_1_05'])
        self.assertIn('1C', result['items'])

    def test_signals_do_not_claim_verified_events_and_keep_amount_changes(self):
        from disclosure_evidence import describe
        first = describe('We could incur fraud losses of $10 million.')
        second = describe('We could incur fraud losses of $20 million.')
        self.assertTrue(first['risk_language'])
        self.assertEqual(first['review_status'], 'unreviewed')
        self.assertNotEqual(first['evidence_fingerprint'], second['evidence_fingerprint'])

    def test_transient_server_failure_is_retried(self):
        from urllib.error import HTTPError
        with patch.object(discovery, 'urlopen') as fetch, patch.object(discovery.time, 'sleep'):
            response = unittest.mock.MagicMock()
            response.__enter__.return_value.read.return_value = b'ok'
            fetch.side_effect = [HTTPError('https://example.org', 502, 'Bad Gateway', {}, None), response]
            self.assertEqual(discovery.SEC().read('https://example.org'), b'ok')
            self.assertEqual(fetch.call_count, 2)

    def test_bundled_company_snapshot(self):
        root = Path(discovery.__file__).parent
        source = root / 'companies.csv'
        with source.open() as company_file:
            rows = list(csv.DictReader(company_file))
        manifest = json.loads((root / 'companies_source.json').read_text())
        self.assertEqual(len(rows), 500)
        self.assertEqual(len({r['cik'] for r in rows}), 500)
        self.assertEqual(len({r['sector'] for r in rows}), 11)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), manifest['csv_sha256'])


if __name__ == '__main__':
    unittest.main()
