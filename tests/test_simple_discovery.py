import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import discovery
from poc_analysis import run_poc


class SimpleDiscoveryTests(unittest.TestCase):
    def test_run_has_no_prompts_no_llm_and_hardcoded_contact(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(discovery, 'ROOT', Path(folder)), \
             patch.object(discovery, 'INPUT_FILE', Path(folder) / 'absent.json'), \
             patch.object(discovery, 'fetch_company', return_value={}) as fetch, \
             patch.object(discovery.scanner, 'main', return_value=0) as scan, \
             patch.object(discovery, 'write_financials_report'), \
             patch('builtins.input', side_effect=AssertionError('Unexpected prompt')), \
             patch('builtins.print'):
            self.assertEqual(discovery.main(), 0)
            fetch.assert_called_once_with('19617', 'FraudResearch andrew@johnson.vet')
            self.assertIn('--sp500-financials', scan.call_args.args[0])
            self.assertNotIn('--llm', scan.call_args.args[0])

    def test_sec_failure_stops_before_sector_scan(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(discovery, 'ROOT', Path(folder)), \
             patch.object(discovery, 'INPUT_FILE', Path(folder) / 'absent.json'), \
             patch.object(discovery, 'fetch_company', side_effect=OSError('403 Forbidden')), \
             patch.object(discovery.scanner, 'main') as scan, patch('builtins.print'):
            self.assertEqual(discovery.main(), 1)
            scan.assert_not_called()
            self.assertIn('blocked', (Path(folder) / 'reports' / 'financials_discovery.md').read_text())

    def test_poc_denominators_and_financial_candidates(self):
        with tempfile.TemporaryDirectory() as folder, patch('builtins.print'):
            source = Path(folder) / 'input.json'
            source.write_text(json.dumps([
                {'ticker': 'A', 'cik': '1', 'sector': 'health_care', 'accession_number': 'a',
                 'status': 'ok', 'item_1a_text': 'Fraud losses were USD 2 million.'},
                {'ticker': 'B', 'cik': '2', 'sector': 'industrials', 'accession_number': 'b',
                 'status': 'ok', 'item_1a_text': 'Credit losses were USD 4 million.'},
                {'ticker': 'C', 'cik': '3', 'sector': 'industrials', 'accession_number': 'c',
                 'status': 'error', 'item_1a_text': ''}]))
            result = run_poc(source, Path(folder) / 'out')
            self.assertEqual(result['records'], 3)
            self.assertEqual(result['readable_records'], 2)
            self.assertEqual(result['literal_fraud_records'], 1)
            self.assertEqual(result['fraud_money_candidates'], 1)
            self.assertEqual(result['llm_calls'], 0)

    def test_bundled_universe_has_valid_ciks_and_matches_manifest(self):
        from fraud_financials import load_ciks
        import hashlib
        root = Path(discovery.__file__).parent / 'universes'
        path = root / 'sp500_financials.csv'
        manifest = json.loads((root / 'sp500_financials_source.json').read_text())
        self.assertEqual(len(load_ciks(path)), manifest['companies'])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), manifest['csv_sha256'])


if __name__ == '__main__':
    unittest.main()
