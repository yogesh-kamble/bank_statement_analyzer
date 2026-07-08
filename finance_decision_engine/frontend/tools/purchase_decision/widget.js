document.addEventListener(
    "DOMContentLoaded",
    function () {

        const paymentMode =
            document.getElementById(
                "paymentMode"
            );

        const emiSection =
            document.getElementById(
                "emiSection"
            );

        function togglePaymentMode() {

            if (
                paymentMode.value === "cash"
            ) {

                emiSection.style.display =
                    "none";

            } else {

                emiSection.style.display =
                    "block";
            }
        }

        paymentMode.addEventListener(
            "change",
            togglePaymentMode
        );

        togglePaymentMode();
    }
);

document
    .getElementById("analyze-btn")
    .addEventListener("click", analyzePurchase);

const paymentMode = document.getElementById("paymentMode");

paymentMode.addEventListener("change", function () {

    const emiSection =
        document.getElementById("emiSection");

    if (this.value === "cash") {
        emiSection.style.display = "none";
    } else {
        emiSection.style.display = "block";
    }
});

async function analyzePurchase() {

    const income = parseFloat(
        document.getElementById("income").value
    );

    const expenses = parseFloat(
        document.getElementById("expenses").value
    );

    const savings = parseFloat(
        document.getElementById("savings").value
    );

    const purchaseAmount = parseFloat(
        document.getElementById("purchase").value
    );

    if (!income || income <= 0) {
        alert("Please enter valid monthly income.");
        return;
    }

    if (!purchaseAmount || purchaseAmount <= 0) {
        alert("Please enter valid purchase amount.");
        return;
    }

    if (expenses < 0 || savings < 0) {
        alert("Values cannot be negative.");
        return;
    }

    const payload = {
        monthly_income: income,
        monthly_expenses: expenses,
        current_savings: savings,

        purchase_amount: purchaseAmount,

        payment_mode:
            document.getElementById(
                "paymentMode"
            ).value,

        down_payment:
            Number(
                document.getElementById(
                    "downPayment"
                )?.value || 0
            ),

        emi_months:
            Number(
                document.getElementById(
                    "emiMonths"
                )?.value || 12
            ),

        annual_interest_rate:
            Number(
                document.getElementById(
                    "interestRate"
                )?.value || 12
            )
    };

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

        console.error(error);

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

    const score = data.decision_score || 0;

    let badgeClass = "safe";

    if (score < 60) {

        badgeClass = "high-risk";

    } else if (score < 80) {

        badgeClass = "moderate";

    }

    const emiRatio = data.emi_ratio || 0;

    document.getElementById("result").innerHTML = `

    <div class="result-card">

        <h2>

            Purchase Analysis

        </h2>

        <div style="text-align:center;margin-bottom:30px;">

            <span class="badge ${badgeClass}">

                ${getDecisionBadge(data.decision)}

            </span>

        </div>

        <div class="score-section">

            <div class="score-header">

                <span>

                    Purchase Decision Score

                </span>

                <strong>

                    ${score}/100

                </strong>

            </div>

            <div class="score-bar">

                <div

                    class="score-fill ${badgeClass}"

                    style="width:${score}%"

                >

                </div>

            </div>

        </div>

        <div class="summary-grid">

            <div class="summary-item">

                <div class="label">

                    Monthly EMI

                </div>

                <div class="value">

                    ₹${Math.round(

                        data.monthly_emi || 0

                    ).toLocaleString()}

                </div>

            </div>

            <div class="summary-item">

                <div class="label">

                    EMI Ratio

                </div>

                <div class="value">

                    ${emiRatio.toFixed(1)}%

                </div>

            </div>

            <div class="summary-item">

                <div class="label">

                    Savings Remaining

                </div>

                <div class="value">

                    ₹${Math.round(

                        data.savings_remaining || 0

                    ).toLocaleString()}

                </div>

            </div>

            <div class="summary-item">

                <div class="label">

                    Emergency Runway

                </div>

                <div class="value">

                    ${data.emergency_runway_months || 0}

                    Months

                </div>

            </div>

        </div>

        <div class="analysis-grid">

            <div class="analysis-card">

                <h3>

                    📊 Assessment

                </h3>

                <p>

                    ${data.headline || ""}

                </p>

            </div>

            <div class="analysis-card">

                <h3>

                    💡 Recommendation

                </h3>

                <p>

                    ${data.recommendation || ""}

                </p>

            </div>

        </div>

        <div class="tip-card">

            <h3>

                💰 Financial Tip

            </h3>

            <p>

                Try to keep your total EMI below
                <strong>30% of your monthly income</strong>.
                Also maintain an emergency fund covering
                at least <strong>6 months of expenses</strong>
                before making large purchases.

            </p>

        </div>

    </div>

    `;
}

function getDecisionBadge(decision) {

    switch ((decision || "").toUpperCase()) {

        case "SAFE":
            return "🟢 SAFE";

        case "MODERATE":
            return "🟠 MODERATE";

        case "RISKY":
        case "HIGH_RISK":
        case "HIGH RISK":
            return "🔴 HIGH RISK";

        default:
            return decision || "N/A";
    }
}

function setLoading(isLoading) {

    const btn = document.getElementById("analyze-btn");

    btn.disabled = isLoading;

    btn.innerHTML = isLoading
        ? "Analyzing..."
        : "Analyze Purchase";
}