from fastapi import FastAPI, UploadFile, File
import shutil
import os
from fastapi.middleware.cors import CORSMiddleware

from backend.tools.statement_analyzer.analyzer import analyze_statement

from backend.tools.purchase_decision.schemas import (
    PurchaseDecisionRequest,
    PurchaseDecisionResponse
)

from backend.tools.purchase_decision.models import (
    PurchaseInput
)

from backend.tools.purchase_decision.analyzer import (
    analyze_purchase
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Financial Decision Engine is running"}


@app.post("/analyze-statement")
async def analyze(file: UploadFile = File(...)):
    file_path = f"temp_{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = analyze_statement(file_path, bank="icici")

    os.remove(file_path)

    return result

@app.post(
    "/api/v1/purchase-decision/analyze",
    response_model=PurchaseDecisionResponse
)
def analyze_purchase_decision(
    request: PurchaseDecisionRequest
):
    data = PurchaseInput(
        monthly_income=request.monthly_income,

        monthly_expenses=request.monthly_expenses,

        current_savings=request.current_savings,

        purchase_amount=request.purchase_amount,

        emi_months=request.emi_months,

        annual_interest_rate=request.annual_interest_rate
    )

    result = analyze_purchase(data)

    return PurchaseDecisionResponse(
        monthly_emi=result.monthly_emi,

        emi_ratio=result.emi_ratio,

        savings_after_purchase=result.savings_after_purchase,

        stress_score=result.stress_score,

        decision=result.decision,

        insight=result.insight,

        recommendation=result.recommendation
    )