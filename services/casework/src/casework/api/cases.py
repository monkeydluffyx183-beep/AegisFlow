from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


@router.get("/contract")
def contract() -> dict[str, list[str]]:
    return {"supported_actions": ["queue", "detail", "assign", "investigate", "disposition", "graph"]}
