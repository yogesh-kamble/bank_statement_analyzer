"""
CLI entry point for ICICI Bank Statement Analyzer.

Usage:
    # Rule-based insights (no AI, no API key needed)
    python main.py statement.csv

    # Claude (Anthropic API) — requires ANTHROPIC_API_KEY
    python main.py statement.csv --client claude

    # Ollama (local) — default model: llama3.2
    python main.py statement.csv --client ollama

    # Ollama with a specific model
    python main.py statement.csv --client ollama --model mistral

    # Claude with a specific model
    python main.py statement.csv --client claude --model claude-sonnet-4-20250514

    # Ollama pointing at a non-default host
    python main.py statement.csv --client ollama --ollama-host http://192.168.1.10:11434
"""

import argparse
import sys
from pathlib import Path

from ai_clients import VALID_CLIENTS, get_client
from analyzer import analyze, build_insight_prompt, parse_insight_response
from parser import parse_icici_csv


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _separator(char: str = "─", width: int = 52) -> str:
    return char * width


def _print_result(result) -> None:
    print()
    print(_separator("═"))
    print("  📊  ICICI BANK STATEMENT ANALYSIS")
    print(_separator("═"))

    print(f"\n  Total Spend      : ₹{result.total_spend:>12,.2f}")
    print(f"  Transactions     : {result.transaction_count:>12}")

    print(f"\n{_separator()}")
    print("  CATEGORY BREAKDOWN")
    print(_separator())

    sorted_cats = sorted(result.category_totals.items(), key=lambda x: x[1], reverse=True)
    for cat, amount in sorted_cats:
        bar_len = int((amount / result.total_spend) * 30) if result.total_spend else 0
        bar = "█" * bar_len
        print(f"  {cat.title():<16} ₹{amount:>10,.2f}  {bar}")

    print(f"\n{_separator()}")
    print("  TOP 3 CATEGORIES")
    print(_separator())
    medals = ["🥇", "🥈", "🥉"]
    for i, (cat, amount) in enumerate(result.top_categories):
        medal = medals[i] if i < 3 else "  "
        print(f"  {medal}  {cat.title():<16} ₹{amount:,.2f}")

    print(f"\n{_separator()}")
    print("  INSIGHTS")
    print(_separator())
    print(f"  💡 {result.insight}")
    print()
    print(f"  ✅ {result.suggestion}")
    print()
    print(_separator("═"))
    print()


# ---------------------------------------------------------------------------
# Rule-based fallback insights (no AI required)
# ---------------------------------------------------------------------------

def _apply_rule_based_insights(result) -> None:
    if result.top_categories:
        top_cat, top_amt = result.top_categories[0]
        pct = (top_amt / result.total_spend * 100) if result.total_spend else 0
        result.insight = (
            f"Your highest spending category is {top_cat.title()} "
            f"at ₹{top_amt:,.2f} ({pct:.1f}% of total spend)."
        )
        result.suggestion = (
            f"Review your {top_cat.title()} expenses — "
            f"reducing this by 20% would save ₹{top_amt * 0.2:,.2f} this month."
        )


# ---------------------------------------------------------------------------
# AI insight fetcher — client-agnostic
# ---------------------------------------------------------------------------

def _fetch_ai_insights(result, client_name: str, model: str | None, ollama_host: str) -> tuple[str, str]:
    """
    Initialize the requested AI client and call it for insights.
    Returns (insight, suggestion) strings.
    Falls back to existing values on any error.
    """
    kwargs = {}
    if client_name == "ollama":
        kwargs["host"] = ollama_host

    try:
        client = get_client(client_name, model=model, **kwargs)
    except (ValueError, RuntimeError) as e:
        print(f"❌ Client setup failed: {e}")
        return result.insight, result.suggestion

    prompt = build_insight_prompt(
        total_spend=result.total_spend,
        category_totals=result.category_totals,
        top_categories=result.top_categories,
    )

    try:
        raw = client.complete(prompt)
        return parse_insight_response(raw)
    except RuntimeError as e:
        print(f"❌ AI call failed: {e}")
        return result.insight, result.suggestion


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    arg_parser = argparse.ArgumentParser(
        description="Analyze an ICICI Bank CSV statement.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  python main.py statement.csv                            # rule-based insights
  python main.py statement.csv --client claude            # Claude (needs ANTHROPIC_API_KEY)
  python main.py statement.csv --client ollama            # Ollama llama3.2 (local)
  python main.py statement.csv --client ollama --model mistral
  python main.py statement.csv --client claude --model claude-sonnet-4-20250514
        """,
    )

    arg_parser.add_argument(
        "csv_file",
        help="Path to ICICI Bank CSV file",
    )
    arg_parser.add_argument(
        "--client",
        choices=VALID_CLIENTS,
        default=None,
        metavar="CLIENT",
        help=f"AI client for insights. Choices: {', '.join(VALID_CLIENTS)}",
    )
    arg_parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model name override. "
            "Claude default: claude-opus-4-20250514 | "
            "Ollama default: llama3.2"
        ),
    )
    arg_parser.add_argument(
        "--ollama-host",
        default="http://localhost:11434",
        help="Ollama server URL (default: http://localhost:11434)",
    )

    args = arg_parser.parse_args()
    csv_path = Path(args.csv_file)

    # ── Parse ──────────────────────────────────────────────────────────────
    print(f"\n📂 Parsing: {csv_path.name} ...")
    try:
        transactions = parse_icici_csv(csv_path)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"❌ CSV format error: {e}")
        sys.exit(1)

    if not transactions:
        print("⚠️  No transactions found in the file.")
        sys.exit(0)

    print(f"✅ Found {len(transactions)} total transactions.")

    # ── Analyze ────────────────────────────────────────────────────────────
    result = analyze(transactions)

    if result.transaction_count == 0:
        print("⚠️  No expense transactions found.")
        sys.exit(0)

    # ── Insights ───────────────────────────────────────────────────────────
    if args.client:
        print(f"🤖 Fetching insights via {args.client.title()} ...")
        insight, suggestion = _fetch_ai_insights(
            result,
            client_name=args.client,
            model=args.model,
            ollama_host=args.ollama_host,
        )
        result.insight    = insight
        result.suggestion = suggestion
    else:
        _apply_rule_based_insights(result)

    # ── Display ────────────────────────────────────────────────────────────
    _print_result(result)


if __name__ == "__main__":
    main()
