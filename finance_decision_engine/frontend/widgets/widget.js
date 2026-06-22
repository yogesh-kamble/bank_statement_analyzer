document
    .getElementById("analyze-btn")
    .addEventListener("click", analyzePurchase);

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

    const expenses = parseFloat(
        document.getElementById("expenses").value
    );

    const savings = parseFloat(
        document.getElementById("savings").value
    );

    const purchase = parseFloat(
        document.getElementById("purchase").value
    );

    if (!income || income <= 0) {
        alert("Please enter valid monthly income.");
        return;
    }

    if (!purchase || purchase <= 0) {
        alert("Please enter valid purchase amount.");
        return;
    }

    if (expenses < 0 || savings < 0) {
        alert("Values cannot be negative.");
        return;
    }

    try {

    setLoading(true);

    const response = await fetch(
        `${CONFIG.API_BASE_URL}/api/v1/purchase-decision/analyze`,
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(payload)
        }
    );

    if (!response.ok) {
        throw new Error("API request failed");
    }

    const data = await response.json();

    renderResult(data);

    } catch (error) {

        document.getElementById("result").innerHTML = `
            <div class="error-box">
                Unable to analyze purchase.
                Please try again later.
            </div>
        `;

    } finally {

        setLoading(false);

    }
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

function setLoading(isLoading) {
    const btn = document.getElementById("analyze-btn");

    btn.disabled = isLoading;

    btn.innerText = isLoading
        ? "Analyzing..."
        : "Analyze Purchase";
}