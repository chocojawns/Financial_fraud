import unittest

from fraud_costs import find_cost_candidates


class CostDraftTests(unittest.TestCase):
    def test_estimate_range_retained_but_not_approved(self):
        text = ('We reported a cybersecurity incident. We preliminarily estimated expenses '
                'of approximately $180 million to $400 million for remediation and '
                'customer reimbursements relating to this Incident.')
        rows = list(find_cost_candidates(text))
        self.assertEqual([r['amount_text'] for r in rows], ['$180 million', '$400 million'])
        self.assertTrue(all(not r['approved_for_totals'] for r in rows))
        self.assertTrue(all(r['amount_reporting_year'] == '' for r in rows))
        self.assertTrue(all(r['currency'] == 'unknown' for r in rows))

    def test_ordinary_credit_default_without_fraud_context_excluded(self):
        self.assertEqual(list(find_cost_candidates('Credit losses were USD 30 million due to customer defaults.')), [])

    def test_regulatory_penalty_is_not_automatically_fraud(self):
        text = 'The CFPB consent order required a civil monetary penalty of $15 million and a redress plan.'
        rows = list(find_cost_candidates(text))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['fraud_connection_hint'], 'regulatory_context_not_verified_fraud')
        self.assertEqual(rows[0]['category_hint'], 'fine_or_settlement')

    def test_explicit_currency_and_no_inferred_year(self):
        rows = list(find_cost_candidates('For 2024 we recognized fraud losses of USD 2 million.'))
        self.assertEqual(rows[0]['currency'], 'USD')
        self.assertEqual(rows[0]['amount_reporting_year'], '')
        self.assertIn('accrual_words', rows[0]['accounting_basis_flags'])


if __name__ == '__main__':
    unittest.main()
