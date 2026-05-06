import csv
from datetime import datetime


def normalize(file_path: str):
    normalized = []

    with open(file_path, "r", encoding="latin1") as f:
        lines = f.readlines()

    # Step 1: Find transaction table header
    header_index = None
    for i, line in enumerate(lines):
        if "DATE,MODE,PARTICULARS,DEPOSITS,WITHDRAWALS,BALANCE" in line.replace(" ", ""):
            header_index = i
            break

    if header_index is None:
        raise ValueError("Transaction table not found in ICICI statement")

    # Step 2: Read only transaction rows
    reader = csv.DictReader(lines[header_index:])

    for row in reader:
        if not row["DATE"]:
            continue  # skip empty rows

        try:
            date = datetime.strptime(row["DATE"], "%d-%m-%Y")
        except:
            continue  # skip invalid rows

        description = (row.get("PARTICULARS") or "").strip().lower()

        deposit = row.get("DEPOSITS") or "0"
        withdrawal = row.get("WITHDRAWALS") or "0"

        try:
            deposit = float(deposit)
        except:
            deposit = 0.0

        try:
            withdrawal = float(withdrawal)
        except:
            withdrawal = 0.0

        # Determine type + amount
        if deposit > 0:
            txn_type = "credit"
            amount = deposit
        elif withdrawal > 0:
            txn_type = "debit"
            amount = withdrawal
        else:
            continue  # skip zero rows (like B/F)

        normalized.append({
            "date": date,
            "amount": amount,
            "type": txn_type,
            "description": description
        })

    return normalized