from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.purchase_decision import router as purchase_router
from backend.routers.statement_analyzer import router as statement_router

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
    return {
        "name": "Financial Decision Engine",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/tools")
def tools():
    return {
        "tools": [
            {
                "name": "Purchase Decision",
                "endpoint": "/api/v1/purchase-decision/analyze"
            },
            {
                "name": "Statement Analyzer",
                "endpoint": "/api/v1/statement-analyzer/analyze"
            }
        ]
    }


app.include_router(purchase_router)
app.include_router(statement_router)