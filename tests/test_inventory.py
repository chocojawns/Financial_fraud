import unittest

from edgar_inventory import filing_rows


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


if __name__ == '__main__':
    unittest.main()
