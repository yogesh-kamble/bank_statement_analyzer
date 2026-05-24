def generate_purchase_insight(
    decision: str,
    stress_score: int
) -> tuple[str, str]:

    if decision == "high_risk":
        return (
            "This purchase may create significant financial stress.",
            "Consider reducing the budget or delaying the purchase."
        )

    if decision == "moderate":
        return (
            "This purchase looks manageable but needs careful planning.",
            "Maintain an emergency buffer before proceeding."
        )

    return (
        "This purchase appears financially comfortable.",
        "You can proceed while maintaining current savings discipline."
    )