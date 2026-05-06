from fastapi import FastAPI, UploadFile, File
import shutil
import os

from backend.tools.statement_analyzer.analyzer import analyze_statement

app = FastAPI()


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