import unittest
from parser import normalize_amount
from categorizer import categorize
from analyzer import aggregate_spend, analyze
from models import Transaction, CategorizedTransaction


class TestBankAnalyzer(unittest.TestCase):

    def test_normalize_amount(self):
        self.assertEqual(normalize_amount("100", ""), -100.0)
        self.assertEqual(normalize_amount("", "200"), 200.0)
        self.assertEqual(normalize_amount("", ""), 0.0)

    def test_categorization(self):
        txn = Transaction("2024-01-01", "Swiggy Order", -300, 1000)
        self.assertEqual(categorize(txn), "food")

    def test_aggregation(self):
        txns = [
            CategorizedTransaction(Transaction("", "", -100, 0), "food"),
            CategorizedTransaction(Transaction("", "", -200, 0), "food"),
        ]
        result = aggregate_spend(txns)
        self.assertEqual(result["food"], 300)

    def test_filter_and_analysis(self):
        txns = [
            Transaction("", "Swiggy", -300, 0),
            Transaction("", "Amazon", -500, 0),
            Transaction("", "Salary", 10000, 0),
        ]

        result = analyze(txns)

        self.assertEqual(result.total_spend, 800)
        self.assertIn("food", result.category_totals)
        self.assertIn("shopping", result.category_totals)

    def test_end_to_end(self):
        txns = [
            Transaction("", "Zomato", -200, 0),
            Transaction("", "Uber Ride", -150, 0),
            Transaction("", "Flipkart", -400, 0),
        ]

        result = analyze(txns)

        self.assertEqual(len(result.top_categories), 3)
        self.assertTrue(result.total_spend > 0)


if __name__ == "__main__":
    unittest.main()