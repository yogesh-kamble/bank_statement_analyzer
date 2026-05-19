from backend.tools.statement_analyzer.cleaner import clean_description


CATEGORY_RULES = {
    "food": [
        "zomato",
        "swiggy",
        "restaurant",
        "cafe",
        "pizza",
        "burger"
    ],

    "shopping": [
        "amazon",
        "flipkart",
        "myntra",
        "ajio"
    ],

    "transport": [
        "uber",
        "ola",
        "fuel",
        "petrol"
    ],

    "bills": [
        "electricity",
        "recharge",
        "rent",
        "wifi",
        "broadband"
    ]
}


def categorize_transaction(description: str) -> str:
    cleaned = clean_description(description)

    for category, keywords in CATEGORY_RULES.items():
        for keyword in keywords:
            if keyword in cleaned:
                return category

    return "other"