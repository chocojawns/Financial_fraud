import unittest
from unittest.mock import patch

from edgar_inventory import company_history, filing_rows


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.company = {
            'name': 'Example Bank', 'cik': '0000019617', 'sic': '6021',
            'sicDescription': 'National Commercial Banks',
            'filings': {'recent': {
                'form': ['10-K', '8-K', '10-Q', '10-K'],
                'filingDate': ['2025-02-01', '2025-03-01', '2025-05-01', '2020-02-01'],
                'accessionNumber': ['0000019617-25-000001'] * 4,
                'primaryDocument': ['report.htm'] * 4,
            }},
        }

    def test_filters_and_source_link(self):
        rows = list(filing_rows(self.company, {'10-K', '8-K'}, '2023-01-01'))
        self.assertEqual([r['form'] for r in rows], ['10-K', '8-K'])
        self.assertEqual(rows[0]['edgar_url'],
                         'https://www.sec.gov/Archives/edgar/data/19617/'
                         '000001961725000001/0000019617-25-000001-index.html')
        self.assertEqual(rows[0]['report_date'], '')

    def test_excludes_nonfinancial_and_unknown_sic(self):
        for sic in ['7372', '', None]:
            self.company['sic'] = sic
            self.assertEqual(list(filing_rows(self.company, {'10-K'}, '2023-01-01')), [])

    def test_historical_submissions_are_merged_and_out_of_range_skipped(self):
        self.company['filings']['files'] = [
            {'name': 'old.json', 'filingFrom': '2020-01-01', 'filingTo': '2021-12-31'},
            {'name': 'ancient.json', 'filingFrom': '2010-01-01', 'filingTo': '2011-12-31'},
        ]
        older = {'form': ['10-K'], 'filingDate': ['2021-02-01'],
                 'accessionNumber': ['0000019617-21-000001']}
        with patch('edgar_inventory.fetch_company', return_value=self.company), \
             patch('edgar_inventory.fetch_submissions_json', return_value=older) as fetch, \
             patch('edgar_inventory.time.sleep'):
            result = company_history('19617', 'Research contact@example.org',
                                     '2020-01-01', '2026-12-31')
        fetch.assert_called_once_with('old.json', 'Research contact@example.org')
        rows = list(filing_rows(result, {'10-K'}, '2020-01-01'))
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[-1]['primary_document'], '')


if __name__ == '__main__':
    unittest.main()
