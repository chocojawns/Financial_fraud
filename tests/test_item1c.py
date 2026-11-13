import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scan_item1c import analyze_html, classify, main


BODY = ('We assess cybersecurity risks and maintain an information security '
        'program overseen by the board. ' * 4)


class Item1CTests(unittest.TestCase):
    def test_toc_removed_tags_and_negation_preserved(self):
        html = ('<p>Item 1C. Cybersecurity 40</p><p>Item 2. Properties 42</p>'
                '<h2>Item 1C. Cybersecurity</h2>'
                '<ix:nonnumeric name="us-gaap:ExampleTextBlock" contextRef="FY">'
                f'<p>{BODY}</p><p>We have not identified any material fraud incidents.</p>'
                '</ix:nonnumeric><h2>Item 2. Properties</h2><p>Not in section.</p>')
        result = analyze_html(html)
        self.assertEqual(result['status'], 'extracted_needs_review')
        self.assertNotIn('Not in section', result['section'])
        self.assertNotIn('Cybersecurity 40', result['section'])
        self.assertIn('not identified', result['passages'][0]['text'])
        self.assertEqual(result['passages'][0]['tags'][0]['context_ref'], 'FY')

    def test_missing_section_is_not_zero_hits(self):
        result = analyze_html('<p>Risk factors: fraud.</p>')
        self.assertEqual(result['status'], 'section_not_found_or_unreliable')
        self.assertIsNone(result['section'])

    def test_zero_keywords_and_hidden_text(self):
        result = analyze_html('<ix:hidden>fraud</ix:hidden>'
                              f'<h2>Item 1C. Cybersecurity</h2><p>{BODY}</p>'
                              '<h2>Item 2. Properties</h2>')
        self.assertEqual(result['status'], 'extracted_needs_review')
        self.assertEqual(result['passages'], [])

    def test_missing_end_heading_requires_review(self):
        result = analyze_html(f'<h2>Item 1C. Cybersecurity</h2>{BODY} fraud')
        self.assertEqual(result['status'], 'section_not_found_or_unreliable')

    def test_llm_rejects_invented_evidence(self):
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                return json.dumps({'choices': [{'finish_reason': 'stop', 'message': {
                    'content': json.dumps({'classification': 'actual_incident',
                                          'summary': 'unsupported',
                                          'ai_connection': 'absent',
                                          'evidence_quotes': ['invented incident']})}}]}).encode()
        with patch('scan_item1c.urlopen', return_value=Response()):
            with self.assertRaises(ValueError):
                classify('We manage fraud risk.', 'test-model', 'test-key')

    def test_local_cli_end_to_end(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'filing.html'
            output = Path(folder) / 'result.jsonl'
            source.write_text(f'<h2>Item 1C. Cybersecurity</h2><p>{BODY}'
                              'We train employees against phishing.</p>'
                              '<h2>Item 2. Properties</h2>')
            run = subprocess.run([sys.executable, 'scan_item1c.py', '--html',
                                  str(source), '--output', str(output)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(output.read_text())
            self.assertIn('phishing', result['passages'][0]['keywords'])
            self.assertEqual(len(result['document_sha256']), 64)

    def test_vscode_run_without_arguments_prompts_and_scans(self):
        company = {'name': 'Example Financial', 'cik': '1818874', 'sic': '6199',
                   'filings': {'recent': {
                       'form': ['10-K'], 'filingDate': ['2026-02-01'],
                       'accessionNumber': ['0001818874-26-000001'],
                       'primaryDocument': ['annual.htm']}}}
        html = (f'<h2>Item 1C. Cybersecurity</h2><p>{BODY}Fraud is a risk.</p>'
                '<h2>Item 2. Properties</h2>').encode()
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                return html
        with tempfile.TemporaryDirectory() as folder, \
             patch('scan_item1c.__file__', str(Path(folder) / 'scan_item1c.py')), \
             patch.dict('os.environ', {'SEC_USER_AGENT': ''}), \
             patch('builtins.input', side_effect=['', 'research@example.org']), \
             patch('builtins.print'), \
             patch('scan_item1c.company_history', return_value=company) as history, \
             patch('scan_item1c.urlopen', return_value=Response()), \
             patch('scan_item1c.time.sleep'):
            self.assertEqual(main([]), 0)
            history.assert_called_once_with('1818874', 'FraudResearch research@example.org',
                                            '2020-01-01', '2026-12-31')
            output = Path(folder) / 'data' / 'item1c.jsonl'
            record = json.loads(output.read_text())
            self.assertIn('fraud', record['passages'][0]['keywords'])

    def test_metadata_failure_returns_failure_with_evidence(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch('scan_item1c.company_history', side_effect=TimeoutError('timed out')), \
             patch('scan_item1c.time.sleep'), patch('builtins.print'):
            output = Path(folder) / 'errors.jsonl'
            result = main(['--ciks', '1818874', '--email', 'research@example.org',
                           '--output', str(output)])
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.read_text())['status'], 'metadata_error')


if __name__ == '__main__':
    unittest.main()
