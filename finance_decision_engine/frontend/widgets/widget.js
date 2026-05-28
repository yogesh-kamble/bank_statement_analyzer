async function analyzePurchase() {

    const payload = {
        monthly_income: parseFloat(
            document.getElementById("income").value
        ),

        monthly_expenses: parseFloat(
            document.getElementById("expenses").value
        ),

        current_savings: parseFloat(
            document.getElementById("savings").value
        ),

        purchase_amount: parseFloat(
            document.getElementById("purchase").value
        ),

        emi_months: parseInt(
            document.getElementById("months").value
        ),

        annual_interest_rate: 12
    };

    const response = await fetch(
        "http://127.0.0.1:8000/api/v1/purchase-decision/analyze",
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(payload)
        }
    );

    const data = await response.json();

    renderResult(data);
}


function renderResult(data) {

    document.getElementById("result").innerHTML = `
        <h2>${data.decision.toUpperCase()}</h2>

        <p>
            <strong>Stress Score:</strong>
            ${data.stress_score}
        </p>

        <p>
            <strong>Monthly EMI:</strong>
            ₹${data.monthly_emi}
        </p>

        <p>
            <strong>Insight:</strong>
            ${data.insight}
        </p>

        <p>
            <strong>Recommendation:</strong>
            ${data.recommendation}
        </p>
    `;
}