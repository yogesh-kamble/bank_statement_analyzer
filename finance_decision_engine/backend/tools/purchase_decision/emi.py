from math import pow


def calculate_emi(
    principal: float,
    annual_interest_rate: float,
    months: int
) -> float:
    """
    Calculate monthly EMI.

    Args:
        principal: Loan amount
        annual_interest_rate: Annual interest rate (%)
        months: Loan tenure in months

    Returns:
        Monthly EMI
    """

    if principal <= 0:
        return 0

    if months <= 0:
        return 0

    # No-interest loan
    if annual_interest_rate <= 0:
        return round(principal / months, 2)

    monthly_rate = (
        annual_interest_rate / 12 / 100
    )

    emi = (
        principal
        * monthly_rate
        * pow(1 + monthly_rate, months)
    ) / (
        pow(1 + monthly_rate, months) - 1
    )

    return round(emi, 2)