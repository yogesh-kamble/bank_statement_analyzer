def calculate_stress_score(
    monthly_income: float,
    monthly_expenses: float,
    monthly_emi: float,
    current_savings: float,
    purchase_amount: float
) -> tuple[int, str]:

    score = 0

    # EMI burden
    emi_ratio = monthly_emi / monthly_income

    if emi_ratio > 0.5:
        score += 40
    elif emi_ratio > 0.3:
        score += 25
    elif emi_ratio > 0.2:
        score += 10

    # Savings impact
    remaining_savings = current_savings - purchase_amount

    if remaining_savings < (monthly_expenses * 3):
        score += 40

    elif remaining_savings < (monthly_expenses * 6):
        score += 20

    # Cash flow pressure
    remaining_income = monthly_income - monthly_expenses - monthly_emi

    if remaining_income < 10000:
        score += 20

    # Decision buckets
    if score >= 70:
        decision = "high_risk"

    elif score >= 40:
        decision = "moderate"

    else:
        decision = "safe"

    return score, decision