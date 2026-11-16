import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fraud_financials import VERSION, enrich, financial_candidates, export_financial_reports, load_ciks
from scan_item1c import analyze_html, classify, main


class FinancialTests(unittest.TestCase):
    def passage(self, text):
        return {'text': text, 'start': 0, 'document_url': 'https://example.org/filing.htm', 'tags': []}

    def test_explicit_loss_number_is_candidate_not_confirmed_loss(self):
        findings = financial_candidates(self.passage('We incurred US$12.5 million in fraud losses.'))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]['normalized_number'], '12500000.0')
        self.assertEqual(findings[0]['currency'], 'USD')
        self.assertEqual(findings[0]['category_candidate'], 'loss')
        self.assertEqual(findings[0]['review_status'], 'unreviewed')
        self.assertEqual(findings[0]['accounting_location'], '')

    def test_ordinary_credit_loss_is_not_fraud(self):
        self.assertEqual(financial_candidates(self.passage('Credit losses were $200 million due to defaults.')), [])
        self.assertEqual(financial_candidates(self.passage('Fraud is a risk. Credit losses were $200 million.')), [])

    def test_dollar_marker_does_not_establish_usd(self):
        finding = financial_candidates(self.passage('Fraud losses totaled $10m.'))[0]
        self.assertEqual(finding['currency'], '')
        self.assertEqual(finding['normalized_number'], '10000000')

    def test_distinguishes_recovery_from_loss_and_flags_ambiguity(self):
        recovery = financial_candidates(self.passage('We received insurance recoveries of USD 3 million for fraud.'))[0]
        # Two recovery-related labels may overlap: do not force a classification.
        self.assertIn(recovery['category_candidate'], {'insurance_recovery', 'ambiguous_or_other'})
        mixed = financial_candidates(self.passage('Fraud losses of $10 million included recoveries of $2 million.'))
        self.assertTrue(all(f['category_candidate'] == 'ambiguous_or_other' for f in mixed))

    def test_hypothetical_and_shared_scale_range_are_not_realized_losses(self):
        findings = financial_candidates(self.passage('Fraud could cause losses between $10 and $20 million.'))
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]['normalized_number'], '')
        self.assertTrue(all(f['statement_basis'] == 'potential_or_conditional' for f in findings))

    def test_no_amount_and_explicit_zero_are_different(self):
        record = enrich({'status': 'extracted_needs_review', 'passages': [self.passage('We monitor fraud risk.')]})
        self.assertEqual(record['financial_discovery_status'], 'fraud_discussion_no_candidate_amount')
        self.assertEqual(financial_candidates(self.passage('Fraud losses were USD 0.'))[0]['normalized_number'], '0')

    def test_overlapping_evidence_is_deduplicated(self):
        passage = self.passage('Fraud losses were USD 10 million.')
        record = enrich({'status': 'extracted_needs_review', 'passages': [dict(passage), dict(passage)]})
        self.assertEqual(record['financial_candidate_count'], 1)

    def test_tag_on_amount_is_distinct_from_tag_elsewhere_in_passage(self):
        record = analyze_html('<p>Fraud losses were $<ix:nonfraction name="example:FraudLoss" '
                              'contextRef="FY">10</ix:nonfraction> million.</p>'
                              '<p>Revenue was $<ix:nonfraction name="us-gaap:Revenues" '
                              'contextRef="FY">200</ix:nonfraction> million.</p>',
                              whole_filing=True, focus='financial')
        record['passages'][0]['document_url'] = 'https://example.org/filing'
        enrich(record)
        finding = record['passages'][0]['financial_candidates'][0]
        self.assertEqual({tag['name'] for tag in finding['amount_xbrl_tags']}, {'example:FraudLoss'})

    def test_batch_cik_file_validated_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'ciks.csv'
            path.write_text('ticker,cik\nJPM,0000019617\nJPM,19617\nBAC,70858\n')
            self.assertEqual(load_ciks(path), ['19617', '70858'])
            path.write_text('19617\nnot-a-cik\n')
            with self.assertRaises(ValueError):
                load_ciks(path)

    def test_coverage_keeps_latest_attempt_and_no_totals(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'data.jsonl'
            record = {'scan_version': VERSION, 'scan_scope': 'all', 'focus': 'financial',
                      'filing': {'cik': '19617', 'accession': 'example'},
                      'status': 'extracted_needs_review',
                      'passages': [self.passage('Fraud losses were USD 10 million.')]}
            enrich(record)
            path.write_text(json.dumps(record) + '\n' + json.dumps(record) + '\n')
            amounts, coverage = export_financial_reports(path)
            with amounts.open(encoding='utf-8-sig', newline='') as source:
                self.assertEqual(len(list(csv.DictReader(source))), 1)
            with coverage.open(encoding='utf-8-sig', newline='') as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['financial_discovery_status'], 'candidate_amounts_found')

    def test_two_cik_pilot_scans_two_filings_each(self):
        def company(cik, *args):
            return {'name': 'Example', 'cik': cik, 'sic': '6021', 'filings': {'recent': {
                'form': ['10-K'] * 3, 'filingDate': ['2026-02-01', '2025-02-01', '2024-02-01'],
                'accessionNumber': [f'{cik}-a', f'{cik}-b', f'{cik}-c'],
                'primaryDocument': ['annual.htm'] * 3}}}
        with tempfile.TemporaryDirectory() as folder, \
             patch('scan_item1c.company_history', side_effect=company), \
             patch('scan_item1c.read_sec', return_value=b'<p>Fraud losses were USD 2 million.</p>') as fetch, \
             patch('scan_item1c.time.sleep'), patch('builtins.print'):
            output = Path(folder) / 'pilot.jsonl'
            self.assertEqual(main(['--ciks', '19617', '70858', '--pilot', '--primary-only',
                                   '--output', str(output)]), 0)
            self.assertEqual(fetch.call_count, 4)
            rows = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual({r['filing']['cik'] for r in rows}, {'19617', '70858'})
            self.assertTrue(all(r['financial_candidate_count'] == 1 for r in rows))

    def test_llm_account_and_period_require_source_support(self):
        text = 'For 2025, fraud losses of USD 2 million were reported in Other expense.'
        value = {'classification': 'actual_incident', 'summary': 'Fraud losses disclosed.',
                 'ai_connection': 'absent', 'evidence_quotes': [text],
                 'financial_findings': [{
                     'category': 'loss', 'amount_text': 'USD 2 million',
                     'evidence_quote': text, 'accounting_location': 'Other expense',
                     'period_text': '2025'}]}
        def response():
            return json.dumps({'choices': [{'finish_reason': 'stop', 'message': {
                'content': json.dumps(value)}}]}).encode()
        with patch('scan_item1c.urlopen') as fetch:
            fetch.return_value.__enter__.return_value.read.side_effect = response
            reviewed = classify(text, 'test-model', 'test-key')
            passage = self.passage(text)
            passage['llm'] = reviewed
            enrich({'status': 'extracted_needs_review', 'passages': [passage]})
            finding = passage['financial_candidates'][0]
            self.assertEqual(finding['accounting_location'], 'Other expense')
            self.assertEqual(finding['amount_reporting_period'], '2025')
            self.assertEqual(finding['review_status'], 'unreviewed')
            value['financial_findings'][0]['period_text'] = '2022'
            with self.assertRaises(ValueError):
                classify(text, 'test-model', 'test-key')


if __name__ == '__main__':
    unittest.main()
