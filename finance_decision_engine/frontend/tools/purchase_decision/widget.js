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

    const meterColor =
        score >= 80
            ? "#16a34a"
            : score >= 60
            ? "#f59e0b"
            : "#dc2626";

    const badge =
        getDecisionBadge(data.decision);

    document.getElementById("result").innerHTML = `
        <div class="result-card">

            <div class="summary-grid">

                <div class="summary-item">
                    <div class="label">Decision</div>
                    <div class="value">${badge}</div>
                </div>

                <div class="summary-item">
                    <div class="label">Monthly EMI</div>
                    <div class="value">
                        ₹${Math.round(
                            data.monthly_emi || 0
                        ).toLocaleString()}
                    </div>
                </div>

                <div class="summary-item">
                    <div class="label">Emergency Runway</div>
                    <div class="value">
                        ${data.emergency_runway_months || 0}
                        months
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

            </div>

            <div class="stress-section">

                <h3>Purchase Decision Score</h3>

                <div class="stress-meter">

                    <div
                        class="stress-fill"
                        style="
                            width:${score}%;
                            background:${meterColor};
                        "
                    ></div>

                </div>

                <div class="score">
                    ${score}/100
                </div>

            </div>

            <div class="insight-box">
                <h3>Assessment</h3>
                <p>
                    ${data.headline || ""}
                </p>
            </div>

            <div class="recommendation-box">
                <h3>Recommendation</h3>
                <p>
                    ${data.recommendation || ""}
                </p>
            </div>

        </div>
    `;
}

function getDecisionBadge(decision) {

    switch (
        (decision || "").toUpperCase()
    ) {

        case "SAFE":
            return "🟢 SAFE";

        case "MODERATE":
            return "🟠 MODERATE";

        case "RISKY":
            return "🔴 RISKY";

        default:
            return decision || "N/A";
    }
}

function setLoading(isLoading) {

    const btn =
        document.getElementById(
            "analyze-btn"
        );

    btn.disabled = isLoading;

    btn.innerText = isLoading
        ? "Analyzing..."
        : "Analyze Purchase";
}