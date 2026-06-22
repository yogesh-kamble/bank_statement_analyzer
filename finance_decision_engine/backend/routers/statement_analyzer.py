from fastapi import APIRouter, UploadFile, File
import shutil
import os
from backend.tools.statement_analyzer.analyzer import analyze_statement

router = APIRouter(
    prefix="/api/v1/statement-analyzer",
    tags=["Statement Analyzer"]
)

@router.post("/analyze-statement")
async def analyze(file: UploadFile = File(...)):
    file_path = f"temp_{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = analyze_statement(file_path, bank="icici")

    os.remove(file_path)

    return result