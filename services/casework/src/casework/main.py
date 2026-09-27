from fastapi import FastAPI

from .api.auth import router as auth_router
from .api.cases import router as cases_router
from .api.sar import router as sar_router

app = FastAPI(title="AegisFlow Casework Service", version="0.1.0")
app.include_router(auth_router)
app.include_router(cases_router)
app.include_router(sar_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "casework"}
