import json
from types import SimpleNamespace

from backend.ai.config import AISettings
from backend.ai.explainer import OpenAIExplainer, explain_purchase, explain_statement
from backend.ai.formatting import inr
from backend.ai.guardrails import find_unsupported_numbers
from backend.ai.models import Explanation
from backend.tools.purchase_decision.analyzer import analyze_purchase
from backend.tools.purchase_decision.models import PurchaseInput

SETTINGS = AISettings("test", "gpt-test", None, True, 5, 0)


class FakeClient:
    """Mimics client.chat.completions.create, returning queued JSON payloads."""

    def __init__(self, *payloads):
        self.payloads = list(payloads)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        data = self.payloads.pop(0)
        if isinstance(data, Exception):
            raise data
        msg = SimpleNamespace(content=json.dumps(data))
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def emi_case():
    data = PurchaseInput(100000, 40000, 300000, 120000, "emi", 20000, 12, 12.0)
    return data, analyze_purchase(data)


def payload(summary, **kw):
    return {"summary": summary, "key_points": kw.get("kp", []),
            "risks": [], "suggestions": []}


def test_inr_indian_grouping():
    assert inr(150000) == "₹1,50,000"
    assert inr(1234567) == "₹12,34,567"
    assert inr(999) == "₹999"
    assert inr(-45000) == "-₹45,000"


def test_engine_exposes_derived_numbers():
    _, r = emi_case()
    assert r.emi_ratio > 0 and r.total_interest > 0 and r.loan_amount == 100000


def test_cash_path_no_longer_crashes():
    r = analyze_purchase(PurchaseInput(100000, 40000, 300000, 120000, "cash"))
    assert r.decision in {"SAFE", "MODERATE", "RISKY"}


def test_ai_output_with_grounded_numbers_is_accepted():
    data, r = emi_case()
    emi = inr(r.monthly_emi)
    client = FakeClient(payload(f"Your EMI is {emi} per month."))
    out = explain_purchase(data, r, OpenAIExplainer(SETTINGS, client))
    assert out.source == "ai" and emi in out.summary
    # prompt must carry engine numbers, and demand JSON schema output
    sent = client.calls[0]
    assert emi in sent["messages"][1]["content"]
    assert sent["response_format"]["json_schema"]["strict"] is True


def test_ai_invented_number_is_retried_then_accepted():
    data, r = emi_case()
    bad = payload("You could save 4,321 by cutting costs.")
    good = payload("Your EMI is manageable.")
    client = FakeClient(bad, good)
    out = explain_purchase(data, r, OpenAIExplainer(SETTINGS, client))
    assert out.source == "ai" and "4,321" not in out.summary
    assert "4321" in client.calls[1]["messages"][-1]["content"].replace(".0", "")


def test_ai_invented_number_twice_falls_back():
    data, r = emi_case()
    bad = payload("Aim for a 37% saving rate.")
    out = explain_purchase(data, r, OpenAIExplainer(SETTINGS, FakeClient(bad, bad)))
    assert out.source == "fallback"
    assert "37%" not in out.summary


def test_api_error_falls_back():
    data, r = emi_case()
    out = explain_purchase(data, r, OpenAIExplainer(SETTINGS, FakeClient(RuntimeError("boom"))))
    assert out.source == "fallback" and r.decision in out.summary


def test_no_api_key_falls_back_without_calling_openai():
    data, r = emi_case()
    ex = OpenAIExplainer(AISettings(None, "m", None, True, 5, 0))
    assert ex.available is False
    assert explain_purchase(data, r, ex).source == "fallback"


def test_statement_facts_computed_in_code_and_grounded():
    agg = {"total_spend": 50000.0, "total_income": 80000.0, "transaction_count": 40,
           "merchant_totals": {"zomato": 10000.0, "amazon": 5000.0, "unknown": 35000.0}}
    client = FakeClient(payload("Net cash flow is ₹30,000.",
                                kp=["Zomato is 20.0% of spend.", "70.0% is unclassified."]))
    out = explain_statement(agg, OpenAIExplainer(SETTINGS, client))
    assert out.source == "ai"
    facts_sent = client.calls[0]["messages"][1]["content"]
    assert "₹30,000" in facts_sent and "37.5%" in facts_sent  # net + savings rate


def test_guardrail_flags_unknown_numbers_only():
    facts = {"a": {"value": 45000, "display": "₹45,000"}}
    ok = Explanation("Spend is ₹45,000.")
    bad = Explanation("Spend is ₹45,000, about 50,000 soon.")
    assert find_unsupported_numbers(ok, facts) == []
    assert find_unsupported_numbers(bad, facts) == [50000.0]
