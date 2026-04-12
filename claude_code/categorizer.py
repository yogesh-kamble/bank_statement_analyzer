"""
Rule-based transaction categorization for ICICI Bank statements.

HOW TO EXTEND:
  Add new categories by inserting a new key and keyword list into CATEGORY_RULES.
  Rules are evaluated top-to-bottom; first match wins.
  Keywords are matched case-insensitively against the transaction description.
"""

# ---------------------------------------------------------------------------
# Category rules: ordered list of (category_name, [keywords])
# First matching category wins. "other" is the guaranteed fallback.
# ---------------------------------------------------------------------------
CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("food", [
        "swiggy", "zomato", "dominos", "pizza", "burger", "mcdonald",
        "kfc", "starbucks", "cafe", "restaurant", "hotel", "dining",
        "biryani", "barbeque", "subway", "dunkin", "haldiram",
    ]),
    ("shopping", [
        "amazon", "flipkart", "myntra", "ajio", "nykaa", "snapdeal",
        "meesho", "bigbasket", "blinkit", "zepto", "grofers",
        "reliance", "dmart", "mall", "store", "shop",
    ]),
    ("bills", [
        "electricity", "bescom", "tata power", "msedcl", "bses",
        "rent", "maintenance", "society",
        "jio", "airtel", "vodafone", "vi ", "bsnl", "recharge",
        "broadband", "internet", "dth", "tatasky", "dish tv",
        "gas", "indane", "hp gas", "bharat gas",
        "insurance", "lic", "premium",
        "emi", "loan",
    ]),
    ("transport", [
        "uber", "ola", "rapido", "meru",
        "irctc", "railway", "train", "flight", "airline", "indigo",
        "air india", "spicejet", "vistara", "goair",
        "bus", "metro", "bmtc", "redbus",
        "petrol", "diesel", "fuel", "hp petrol", "ioc", "bharat petroleum",
        "parking", "toll", "fastag",
    ]),
    ("health", [
        "pharmacy", "medplus", "apollo", "netmeds", "1mg",
        "hospital", "clinic", "doctor", "lab", "diagnostic",
        "thyrocare", "lal path", "practo",
    ]),
    ("entertainment", [
        "netflix", "hotstar", "prime video", "amazon prime",
        "spotify", "gaana", "wynk",
        "bookmyshow", "pvr", "inox", "cinepolis",
        "youtube", "google play", "apple store",
        "gaming", "steam",
    ]),
    ("education", [
        "udemy", "coursera", "unacademy", "byju", "vedantu",
        "school", "college", "university", "tuition",
        "books", "stationery",
    ]),
    ("investments", [
        "zerodha", "groww", "upstox", "kuvera", "coin",
        "mutual fund", "sip", "nps", "ppf", "fd ",
        "stocks", "equity", "demat",
    ]),
    # "other" is added programmatically as fallback — do not add here
]


def categorize(description: str) -> str:
    """
    Return a category name for a transaction description.

    Args:
        description: Raw transaction description string.

    Returns:
        Category name string. Falls back to "other" if no rule matches.
    """
    normalized = description.lower()
    for category, keywords in CATEGORY_RULES:
        if any(keyword in normalized for keyword in keywords):
            return category
    return "other"
