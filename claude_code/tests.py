"""
Unit tests for ICICI Bank Statement Analyzer.

Run with:
    cd bank_analyzer
    python -m pytest tests.py -v

Or without pytest:
    python tests.py
"""

import csv
import os
import sys
import tempfile
import unittest

# Make sure imports resolve from this directory
sys.path.insert(0, os.path.dirname(__file__))

from analyzer import (
    aggregate_spend,
    analyze,
    filter_expenses,
    categorize_transactions,
    get_top_categories,
    build_insight_prompt,
    parse_insight_response,
)
from categorizer import categorize
from models import AnalysisResult, CategorizedTransaction, Transaction
from parser import normalize_amount, parse_icici_csv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_transaction(description: str, amount: float, date: str = "01/01/2024") -> Transaction:
    return Transaction(date=date, description=description, amount=amount, balance=10000.0)


def write_temp_csv(rows: list[dict], headers: list[str] | None = None) -> str:
    """Write rows to a temp CSV file and return its path."""
    if headers is None:
        headers = ["DATE", "MODE", "PARTICULARS", "DEPOSITS", "WITHDRAWALS", "BALANCE"]

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    )
    writer = csv.DictWriter(tmp, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    tmp.close()
    return tmp.name


# ---------------------------------------------------------------------------
# 1. CSV Parsing
# ---------------------------------------------------------------------------

class TestCSVParsing(unittest.TestCase):
    def setUp(self):
        self.csv_path = write_temp_csv([
            {"DATE": "01/01/2024", "MODE": "UPI",  "PARTICULARS": "SWIGGY ORDER",    "WITHDRAWALS": "450.00",   "DEPOSITS": "",         "BALANCE": "9550.00"},
            {"DATE": "02/01/2024", "MODE": "CR",   "PARTICULARS": "SALARY CREDIT",   "WITHDRAWALS": "",         "DEPOSITS": "50000.00", "BALANCE": "59550.00"},
            {"DATE": "03/01/2024", "MODE": "UPI",  "PARTICULARS": "AMAZON PURCHASE", "WITHDRAWALS": "1299.00",  "DEPOSITS": "",         "BALANCE": "58251.00"},
            {"DATE": "04/01/2024", "MODE": "UPI",  "PARTICULARS": "UPI-ZEPTO",       "WITHDRAWALS": "230.00",   "DEPOSITS": "",         "BALANCE": "58021.00"},
        ])

    def tearDown(self):
        os.unlink(self.csv_path)

    def test_correct_row_count(self):
        txns = parse_icici_csv(self.csv_path)
        self.assertEqual(len(txns), 4)

    def test_description_preserved(self):
        txns = parse_icici_csv(self.csv_path)
        descriptions = [t.description for t in txns]
        self.assertIn("SWIGGY ORDER", descriptions)
        self.assertIn("SALARY CREDIT", descriptions)

    def test_debit_is_negative(self):
        txns = parse_icici_csv(self.csv_path)
        swiggy = next(t for t in txns if "SWIGGY" in t.description)
        self.assertAlmostEqual(swiggy.amount, -450.00)

    def test_credit_is_positive(self):
        txns = parse_icici_csv(self.csv_path)
        salary = next(t for t in txns if "SALARY" in t.description)
        self.assertAlmostEqual(salary.amount, 50000.00)

    def test_balance_parsed(self):
        txns = parse_icici_csv(self.csv_path)
        self.assertAlmostEqual(txns[0].balance, 9550.00)

    def test_file_not_found_raises(self):
        with self.assertRaises(FileNotFoundError):
            parse_icici_csv("/non/existent/file.csv")

    def test_missing_required_columns_raises(self):
        bad_csv = write_temp_csv(
            [{"Name": "Alice", "Amount": "100"}],
            headers=["Name", "Amount"]
        )
        try:
            with self.assertRaises(ValueError):
                parse_icici_csv(bad_csv)
        finally:
            os.unlink(bad_csv)

    def test_skips_blank_rows(self):
        path = write_temp_csv([
            {"DATE": "01/01/2024", "MODE": "UPI", "PARTICULARS": "SWIGGY", "WITHDRAWALS": "100", "DEPOSITS": "", "BALANCE": "900"},
            {"DATE": "",           "MODE": "",     "PARTICULARS": "",       "WITHDRAWALS": "",    "DEPOSITS": "", "BALANCE": ""},
            {"DATE": "02/01/2024", "MODE": "UPI", "PARTICULARS": "OLA",    "WITHDRAWALS": "200", "DEPOSITS": "", "BALANCE": "700"},
        ])
        try:
            txns = parse_icici_csv(path)
            self.assertEqual(len(txns), 2)
        finally:
            os.unlink(path)

    def test_handles_comma_formatted_amounts(self):
        path = write_temp_csv([
            {"DATE": "01/01/2024", "MODE": "NEFT", "PARTICULARS": "RENT", "WITHDRAWALS": "25,000.00", "DEPOSITS": "", "BALANCE": "100000.00"},
        ])
        try:
            txns = parse_icici_csv(path)
            self.assertAlmostEqual(txns[0].amount, -25000.00)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# 2. Debit/Credit Normalization
# ---------------------------------------------------------------------------

class TestNormalizeAmount(unittest.TestCase):
    def test_debit_becomes_negative(self):
        self.assertAlmostEqual(normalize_amount("500.00", ""), -500.00)

    def test_credit_becomes_positive(self):
        self.assertAlmostEqual(normalize_amount("", "10000.00"), 10000.00)

    def test_both_empty_returns_zero(self):
        self.assertAlmostEqual(normalize_amount("", ""), 0.0)

    def test_debit_takes_precedence(self):
        # Edge case: debit wins if both present
        self.assertAlmostEqual(normalize_amount("100.00", "200.00"), -100.00)

    def test_handles_zero_debit(self):
        self.assertAlmostEqual(normalize_amount("0", ""), 0.0)

    def test_handles_whitespace(self):
        self.assertAlmostEqual(normalize_amount("  750.50  ", ""), -750.50)

    def test_handles_comma_in_amount(self):
        self.assertAlmostEqual(normalize_amount("1,23,456.78", ""), -123456.78)

    def test_invalid_string_returns_zero(self):
        self.assertAlmostEqual(normalize_amount("N/A", ""), 0.0)


# ---------------------------------------------------------------------------
# 3. Categorization
# ---------------------------------------------------------------------------

class TestCategorize(unittest.TestCase):
    cases = [
        ("SWIGGY ORDER 98765",        "food"),
        ("ZOMATO FOOD DELIVERY",       "food"),
        ("AMAZON PURCHASE",            "shopping"),
        ("FLIPKART ORDER",             "shopping"),
        ("UBER TRIP",                  "transport"),
        ("OLA RIDE",                   "transport"),
        ("IRCTC TICKET BOOKING",       "transport"),
        ("AIRTEL RECHARGE",            "bills"),
        ("JIO BROADBAND PAYMENT",      "bills"),
        ("ELECTRICITY BESCOM",         "bills"),
        ("NETFLIX SUBSCRIPTION",       "entertainment"),
        ("BOOKMYSHOW TICKET",          "entertainment"),
        ("APOLLO PHARMACY",            "health"),
        ("GROWW MUTUAL FUND SIP",      "investments"),
        ("UDEMY COURSE PURCHASE",      "education"),
        ("RANDOM UNKNOWN MERCHANT",    "other"),
    ]

    def test_all_categorization_cases(self):
        for description, expected_category in self.cases:
            with self.subTest(description=description):
                self.assertEqual(
                    categorize(description),
                    expected_category,
                    msg=f"'{description}' should be '{expected_category}'",
                )

    def test_case_insensitive(self):
        self.assertEqual(categorize("swiggy order"), "food")
        self.assertEqual(categorize("SWIGGY ORDER"), "food")
        self.assertEqual(categorize("Swiggy Order"), "food")

    def test_fallback_to_other(self):
        self.assertEqual(categorize(""), "other")
        self.assertEqual(categorize("NEFT TRANSFER XYZ123"), "other")


# ---------------------------------------------------------------------------
# 4. Aggregation
# ---------------------------------------------------------------------------

class TestAggregateSpend(unittest.TestCase):
    def setUp(self):
        self.transactions = [
            make_transaction("SWIGGY ORDER",   -200.0),
            make_transaction("ZOMATO FOOD",    -350.0),
            make_transaction("AMAZON PURCHASE", -999.0),
            make_transaction("OLA RIDE",        -150.0),
            make_transaction("UBER TRIP",       -200.0),
            make_transaction("RANDOM STUFF",    -500.0),
        ]

    def test_category_totals_are_correct(self):
        categorized = categorize_transactions(self.transactions)
        totals = aggregate_spend(categorized)

        self.assertAlmostEqual(totals["food"],      550.0)   # 200 + 350
        self.assertAlmostEqual(totals["shopping"],  999.0)
        self.assertAlmostEqual(totals["transport"], 350.0)   # 150 + 200
        self.assertAlmostEqual(totals["other"],     500.0)

    def test_all_amounts_are_positive(self):
        categorized = categorize_transactions(self.transactions)
        totals = aggregate_spend(categorized)
        for category, amount in totals.items():
            self.assertGreater(amount, 0, f"{category} total should be positive")

    def test_empty_returns_empty_dict(self):
        self.assertEqual(aggregate_spend([]), {})

    def test_top_categories_sorted_descending(self):
        categorized = categorize_transactions(self.transactions)
        totals = aggregate_spend(categorized)
        top = get_top_categories(totals, n=3)

        amounts = [spend for _, spend in top]
        self.assertEqual(amounts, sorted(amounts, reverse=True))

    def test_top_categories_limited_to_n(self):
        categorized = categorize_transactions(self.transactions)
        totals = aggregate_spend(categorized)
        top = get_top_categories(totals, n=2)
        self.assertLessEqual(len(top), 2)


# ---------------------------------------------------------------------------
# 5. Filter Expenses
# ---------------------------------------------------------------------------

class TestFilterExpenses(unittest.TestCase):
    def test_only_negatives_returned(self):
        txns = [
            make_transaction("DEBIT",  -100.0),
            make_transaction("SALARY",  50000.0),
            make_transaction("REFUND",  200.0),
            make_transaction("SPEND",  -500.0),
        ]
        expenses = filter_expenses(txns)
        self.assertEqual(len(expenses), 2)
        self.assertTrue(all(t.amount < 0 for t in expenses))

    def test_zero_amount_excluded(self):
        txns = [make_transaction("ZERO", 0.0)]
        self.assertEqual(filter_expenses(txns), [])

    def test_all_credits_returns_empty(self):
        txns = [make_transaction("CREDIT", 1000.0) for _ in range(5)]
        self.assertEqual(filter_expenses(txns), [])


# ---------------------------------------------------------------------------
# 6. End-to-End Analysis
# ---------------------------------------------------------------------------

class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.csv_path = write_temp_csv([
            {"DATE": "01/01/2024", "MODE": "CR",   "PARTICULARS": "SALARY",          "DEPOSITS": "60000", "WITHDRAWALS": "",     "BALANCE": "60000"},
            {"DATE": "02/01/2024", "MODE": "UPI",  "PARTICULARS": "SWIGGY ORDER",    "DEPOSITS": "",      "WITHDRAWALS": "500",  "BALANCE": "59500"},
            {"DATE": "03/01/2024", "MODE": "UPI",  "PARTICULARS": "AMAZON PURCHASE", "DEPOSITS": "",      "WITHDRAWALS": "2999", "BALANCE": "56501"},
            {"DATE": "04/01/2024", "MODE": "UPI",  "PARTICULARS": "OLA RIDE",        "DEPOSITS": "",      "WITHDRAWALS": "200",  "BALANCE": "56301"},
            {"DATE": "05/01/2024", "MODE": "UPI",  "PARTICULARS": "ZOMATO FOOD",     "DEPOSITS": "",      "WITHDRAWALS": "750",  "BALANCE": "55551"},
            {"DATE": "06/01/2024", "MODE": "NEFT", "PARTICULARS": "ELECTRICITY BILL","DEPOSITS": "",      "WITHDRAWALS": "1800", "BALANCE": "53751"},
            {"DATE": "07/01/2024", "MODE": "UPI",  "PARTICULARS": "NETFLIX",         "DEPOSITS": "",      "WITHDRAWALS": "649",  "BALANCE": "53102"},
        ])

    def tearDown(self):
        os.unlink(self.csv_path)

    def test_full_pipeline_runs(self):
        txns = parse_icici_csv(self.csv_path)
        result = analyze(txns)
        self.assertIsInstance(result, AnalysisResult)

    def test_total_spend_correct(self):
        txns = parse_icici_csv(self.csv_path)
        result = analyze(txns)
        # 500 + 2999 + 200 + 750 + 1800 + 649 = 6898
        self.assertAlmostEqual(result.total_spend, 6898.0)

    def test_transaction_count_excludes_credits(self):
        txns = parse_icici_csv(self.csv_path)
        result = analyze(txns)
        self.assertEqual(result.transaction_count, 6)  # salary excluded

    def test_top_categories_max_3(self):
        txns = parse_icici_csv(self.csv_path)
        result = analyze(txns)
        self.assertLessEqual(len(result.top_categories), 3)

    def test_top_categories_descending(self):
        txns = parse_icici_csv(self.csv_path)
        result = analyze(txns)
        amounts = [spend for _, spend in result.top_categories]
        self.assertEqual(amounts, sorted(amounts, reverse=True))

    def test_food_category_combined(self):
        txns = parse_icici_csv(self.csv_path)
        result = analyze(txns)
        # Swiggy 500 + Zomato 750 = 1250
        self.assertAlmostEqual(result.category_totals.get("food", 0), 1250.0)

    def test_category_totals_sum_equals_total_spend(self):
        txns = parse_icici_csv(self.csv_path)
        result = analyze(txns)
        cat_sum = sum(result.category_totals.values())
        self.assertAlmostEqual(cat_sum, result.total_spend, places=1)


# ---------------------------------------------------------------------------
# 7. Insight Prompt + Parsing
# ---------------------------------------------------------------------------

class TestInsightPrompt(unittest.TestCase):
    def test_prompt_contains_total_spend(self):
        prompt = build_insight_prompt(
            total_spend=5000.0,
            category_totals={"food": 2000.0, "shopping": 3000.0},
            top_categories=[("shopping", 3000.0), ("food", 2000.0)],
        )
        self.assertIn("5,000.00", prompt)

    def test_parse_valid_response(self):
        raw = "INSIGHT: You spent a lot on food.\nSUGGESTION: Cook at home twice a week."
        insight, suggestion = parse_insight_response(raw)
        self.assertEqual(insight, "You spent a lot on food.")
        self.assertEqual(suggestion, "Cook at home twice a week.")

    def test_parse_handles_missing_fields(self):
        insight, suggestion = parse_insight_response("Some random text")
        self.assertIn("Unable", insight)
        self.assertIn("Unable", suggestion)


# ---------------------------------------------------------------------------
# 8. AI Clients
# ---------------------------------------------------------------------------

class TestAIClients(unittest.TestCase):
    def test_invalid_client_name_raises(self):
        from ai_clients import get_client
        with self.assertRaises(ValueError):
            get_client("gpt4")

    def test_claude_missing_api_key_raises(self):
        from ai_clients import ClaudeClient
        with self.assertRaises(RuntimeError):
            ClaudeClient(api_key="")

    def test_ollama_missing_package_raises(self):
        """Simulate ollama package not installed."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "ollama":
                raise ImportError("No module named 'ollama'")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = mock_import
        try:
            from ai_clients import OllamaClient
            with self.assertRaises(RuntimeError) as ctx:
                OllamaClient()
            self.assertIn("pip install ollama", str(ctx.exception))
        finally:
            builtins.__import__ = real_import

    def test_get_client_returns_claude(self):
        from ai_clients import ClaudeClient, get_client
        # Skip if anthropic not installed
        try:
            import anthropic  # noqa: F401
        except ImportError:
            self.skipTest("anthropic not installed")
        import os
        os.environ.setdefault("ANTHROPIC_API_KEY", "sk-test-fake-key-for-unit-test")
        client = get_client("claude")
        self.assertIsInstance(client, ClaudeClient)

    def test_valid_client_names(self):
        from ai_clients import VALID_CLIENTS
        self.assertIn("claude", VALID_CLIENTS)
        self.assertIn("ollama", VALID_CLIENTS)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
