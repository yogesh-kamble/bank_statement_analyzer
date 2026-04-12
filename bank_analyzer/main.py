from parser import parse_icici_csv
from analyzer import analyze
from ai_clients.ollama_client import ollama_llm  # or openai_llm

transactions = parse_icici_csv("./test_data/bank_statement.csv")

result = analyze(transactions, llm_client=ollama_llm)

print("Total Spend:", result.total_spend)
print("Top Categories:", result.top_categories)
print("Insight:", result.insight)
print("Suggestion:", result.suggestion)