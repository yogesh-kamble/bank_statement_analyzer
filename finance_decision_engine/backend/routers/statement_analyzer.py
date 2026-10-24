from fastapi import APIRouter, UploadFile, File
import shutil
import os
import uuid
from backend.tools.statement_analyzer.analyzer import analyze_statement

router = APIRouter(
    prefix="/api/v1/statement-analyzer",
    tags=["Statement Analyzer"]
)

# Plain `def` so FastAPI runs it in a threadpool (the OpenAI call is blocking).
@router.post("/analyze-statement")
def analyze(
    file: UploadFile = File(...),
    explain: bool = True
):
    file_path = f"temp_{uuid.uuid4().hex}_{os.path.basename(file.filename or 'statement')}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        return analyze_statement(
            file_path, bank="icici", explain=explain
        )
    finally:
        os.remove(file_path)
