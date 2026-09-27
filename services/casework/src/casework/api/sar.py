from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/sar", tags=["sar"])


@router.get("/contract")
def contract() -> dict[str, list[str]]:
    return {"supported_actions": ["draft", "edit", "approve", "export"], "approval": ["human", "rationale", "immutable_audit"]}
