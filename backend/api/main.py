from fastapi import FastAPI

from backend.api.routes import router

app = FastAPI(
    title="RetailSignal OS API",
    description="Research API for explainable alternative-data Signal Cards.",
    version="0.1.0",
)
app.include_router(router)
