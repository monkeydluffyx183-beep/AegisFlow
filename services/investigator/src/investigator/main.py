from fastapi import FastAPI

app = FastAPI(title="AegisFlow Investigator Service", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "investigator"}


@app.post("/cases/{case_id}/investigate")
def investigate(case_id: str) -> dict[str, str]:
    return {"case_id": case_id, "job_id": f"job-{case_id}", "status": "queued"}
