def calculate_emi(
    principal: float,
    annual_interest_rate: float,
    months: int
) -> float:

    monthly_rate = annual_interest_rate / 12 / 100

    emi = (
        principal
        * monthly_rate
        * (1 + monthly_rate) ** months
    ) / (
        ((1 + monthly_rate) ** months) - 1
    )

    return round(emi, 2)