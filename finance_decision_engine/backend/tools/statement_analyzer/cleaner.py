import re


NOISE_WORDS = [
    "upi",
    "pos",
    "neft",
    "imps",
    "rtgs",
    "transfer",
    "payment",
    "txn",
    "ref",
]


def clean_description(description: str) -> str:
    """
    Clean transaction description into normalized merchant text.
    """

    description = description.lower()

    # Replace separators with spaces
    description = re.sub(r"[/\\\-_]", " ", description)

    # Remove numbers
    description = re.sub(r"\d+", " ", description)

    # Remove extra spaces
    description = re.sub(r"\s+", " ", description).strip()

    # Remove noise words
    words = [
        word
        for word in description.split()
        if word not in NOISE_WORDS
    ]

    return " ".join(words)

KNOWN_MERCHANTS = [
    "zomato",
    "swiggy",
    "amazon",
    "flipkart",
    "uber",
    "ola",
    "myntra",
]


def extract_merchant(description: str) -> str:
    cleaned = clean_description(description)

    for merchant in KNOWN_MERCHANTS:
        if merchant in cleaned:
            return merchant

    return "unknown"