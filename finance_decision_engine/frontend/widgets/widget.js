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

    const meterColor =
    data.stress_score >= 70
        ? "#dc2626"
        : data.stress_score >= 40
        ? "#f59e0b"
        : "#16a34a";

    const badge = getDecisionBadge(data.decision);

    document.getElementById("result").innerHTML = `
        <div class="result-card">

            <div class="summary-grid">

                <div class="summary-item">
                    <div class="label">Monthly EMI</div>
                    <div class="value">
                        ₹${Math.round(data.monthly_emi).toLocaleString()}
                    </div>
                </div>

                <div class="summary-item">
                    <div class="label">Savings Left</div>
                    <div class="value">
                        ₹${Math.round(
                            data.savings_after_purchase
                        ).toLocaleString()}
                    </div>
                </div>

                <div class="summary-item">
                    <div class="label">Risk Level</div>
                    <div class="value">${badge}</div>
                </div>

            </div>

            <div class="stress-section">

                <h3>Financial Stress Score</h3>

                <div class="stress-meter">
                    <div
                        class="stress-fill"
                        style="
                            width:${data.stress_score}%;
                            background:${meterColor};
                        "
                    ></div>
                </div>

                <div class="score">
                    ${data.stress_score}/100
                </div>

            </div>

            <div class="insight-box">
                <h3>Insight</h3>
                <p>${data.insight}</p>
            </div>

            <div class="recommendation-box">
                <h3>Recommendation</h3>
                <p>${data.recommendation}</p>
            </div>

        </div>
    `;
}

function getDecisionBadge(decision) {
    switch (decision) {

        case "safe":
            return "🟢 SAFE";

        case "moderate":
            return "🟠 MODERATE";

        case "high_risk":
            return "🔴 HIGH RISK";

        default:
            return decision;
    }
}