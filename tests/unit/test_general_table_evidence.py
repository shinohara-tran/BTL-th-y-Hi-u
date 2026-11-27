"""Metric/period regression cases independent of issuer names and model scores."""
import unittest
import json
from pathlib import Path
from hybrid_search.retrieval.extractor import AnswerExtractor as E


class GeneralTableEvidenceTests(unittest.TestCase):
    def test_six_existing_demos_on_real_final_chunks(self):
        cases = json.loads((Path(__file__).parents[1] / 'fixtures/part4_demo_rows.json').read_text(encoding='utf-8'))
        self.assertEqual(len(cases), 6)
        for case in cases:
            with self.subTest(query=case['query']):
                answer = E.extract(case['query'],case['text'],company=case['company'],ticker=case['ticker'])
                self.assertTrue(answer.exact_answer.endswith(case['expected_suffix']), answer.exact_answer)

    def test_real_final_chunks_cover_all_thirteen_issuers(self):
        cases = json.loads((Path(__file__).parents[1] / 'fixtures/part4_final_rows.json').read_text(encoding='utf-8'))
        self.assertEqual(len({c['ticker'] for c in cases}), 13)
        for case in cases:
            with self.subTest(ticker=case['ticker']):
                answer=E.extract(case['query'],case['text'],company=case['company'],ticker=case['ticker'])
                if case['expected_suffix']:
                    self.assertTrue(answer.exact_answer.endswith(case['expected_suffix']), answer.exact_answer)
                else:
                    self.assertEqual(answer.exact_answer, '')

    def test_short_issuer_queries_on_real_final_chunks(self):
        cases = json.loads((Path(__file__).parents[1] / 'fixtures/part4_final_rows.json').read_text(encoding='utf-8'))
        demos = json.loads((Path(__file__).parents[1] / 'fixtures/part4_demo_rows.json').read_text(encoding='utf-8'))
        by_ticker = {case['ticker']: case for case in cases}
        by_ticker['AAPL'] = next(case for case in demos if 'Services net sales' in case['query'])
        queries = {
            'JPM': 'JPMorgan basic EPS FY2024',
            'AAPL': 'Apple Services net sales FY2024',
            'LLY': 'Eli Lilly total revenue FY2024',
            'NVDA': 'NVIDIA basic weighted average shares FY2025',
        }
        for ticker, query in queries.items():
            with self.subTest(ticker=ticker):
                case = by_ticker[ticker]
                answer = E.extract(query, case['text'], company=case['company'], ticker=ticker)
                self.assertTrue(answer.exact_answer.endswith(case['expected_suffix']), answer.exact_answer)

    def extract(self, query, rows, header='10-K FY2025'):
        return E.extract(query, f'[{header}]\n\n{rows}')

    def test_nvidia_wrong_year_rejected_correct_column_selected(self):
        q = "What were NVIDIA's basic weighted average shares in fiscal 2025?"
        old = 'Basic weighted average shares (Year Ended): January 29,2023 = 2,487; January 30,2022 = 2,496. Unit: millions of shares.'
        current = 'Basic weighted average shares (Year Ended): Jan 26,2025 = 24,555; Jan 28,2024 = 24,690; Jan 29,2023 = 24,870. Unit: millions of shares.'
        self.assertEqual(self.extract(q, old).exact_answer, '')
        self.assertEqual(self.extract(q, current).exact_answer, 'Basic weighted average shares - FY2025: 24,555 million shares')

    def test_apple_eps_is_single_year_and_not_share_count(self):
        q = "What was Apple's basic earnings per share in fiscal 2025?"
        row = 'Basic earnings per share (Years ended): September 27,2025 = $7.49; September 28,2024 = $6.11. Unit: USD per share.'
        self.assertEqual(self.extract(q, row).exact_answer, 'Basic earnings per share - FY2025: $7.49 per share')
        for changed in (row.replace('Basic earnings per share', 'Weighted-average basic shares outstanding'), row.replace('Basic', 'Diluted')):
            self.assertEqual(self.extract(q, changed).exact_answer, '')

    def test_column_year_not_filing_year(self):
        row = 'Net income: 2025 = 12; 2024 = 9. Unit: millions of USD.'
        self.assertEqual(self.extract('What was net income in fiscal 2024?', row).exact_answer, 'Net income - FY2024: $9 million')

    def test_other_issuer_same_metric_is_not_an_answer(self):
        row = 'Basic weighted average shares: 2025 = 24,555. Unit: millions of shares.'
        answer=E.extract("What were NVIDIA's basic weighted average shares in fiscal 2025?", row, company='Microsoft Corporation', ticker='MSFT')
        self.assertEqual(answer.exact_answer, '')

    def test_rejects_missing_duplicate_and_conflicting_columns(self):
        q = 'What was total revenue in fiscal 2024?'
        for row in ('Total revenue: amount = 12. Unit: millions of USD.',
                    'Total revenue: 2024 = 12; 2024 = 9. Unit: millions of USD.',
                    'Total revenue: 2024 = 12. Unit: unknown unit.',
                    'Total revenue: 2024 = 12. Unit: USD per share.',
                    'Total revenue: 2024 = 12. Unit: millions of shares.',
                    'Total revenue: 2024 = 12. Unit: %.'):
            with self.subTest(row=row): self.assertEqual(self.extract(q, row).exact_answer, '')

    def test_scope_not_region_or_cost(self):
        for label in ('U.S. revenue', 'Services revenue', 'Cost of revenue', 'Revenue'):
            self.assertEqual(self.extract('What was total revenue in fiscal 2024?', f'{label}: 2024 = 12. Unit: millions of USD.').exact_answer, '')
        self.assertEqual(self.extract('What was net income in fiscal 2024?', 'Net income (attributable to noncontrolling interests): 2024 = 12. Unit: millions of USD.').exact_answer, '')

    def test_explicit_segment_supported_without_company_rules(self):
        row = 'Automotive revenue: 2024 = 123. Unit: millions of USD.'
        self.assertEqual(self.extract("What was ExampleCo's automotive revenue in fiscal 2024?", row).exact_answer, 'Automotive revenue - FY2024: $123 million')

    def test_quarter_requires_evidence_and_excludes_ytd(self):
        q = "What was ExampleCo's net income in Q3 FY2025?"
        row = 'Net income: Three Months Ended June 28, 2025 = 12; Nine Months Ended June 28, 2025 = 30. Unit: millions of USD.'
        self.assertEqual(self.extract(q, 'Q3 FY2025\n'+row, '10-Q').exact_answer, 'Net income - Q3 FY2025: $12 million')
        for prefix in ('', 'Q2 FY2025\n', 'Q3 FY2025\nQ2 FY2025\n'):
            self.assertEqual(self.extract(q, prefix+row, '10-Q').exact_answer, '')
        self.assertEqual(self.extract('What was net income in full fiscal year 2025?', row, '10-Q').exact_answer, '')

    def test_ambiguous_multiple_rows_abstains(self):
        row = 'Net income: 2024 = 12. Unit: millions of USD.\nNet income: 2024 = 9. Unit: millions of USD.'
        self.assertEqual(self.extract('What was net income in fiscal 2024?', row).exact_answer, '')

    def test_negative_values_and_percentage_unit(self):
        self.assertEqual(self.extract('What was net income in fiscal 2024?', 'Net income: 2024 = (12.5). Unit: millions of USD.').exact_answer, 'Net income - FY2024: $(12.5) million')
        self.assertEqual(self.extract('What was gross margin percentage in fiscal 2024?', 'Gross margin percentage: 2024 = 35.2%. Unit: %.').exact_answer, 'Gross margin percentage - FY2024: 35.2%')

    def test_missing_year_in_narrative_never_high_confidence(self):
        self.assertEqual(E._evidence_score('What was net income in fiscal 2025?', 'Net income in 2023 was $10 million.', '[10-K FY2025]'), 0)


if __name__ == '__main__':
    unittest.main()
