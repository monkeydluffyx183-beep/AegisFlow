from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/roles")
def roles() -> dict[str, list[str]]:
    return {"roles": ["fraud_analyst", "aml_analyst", "manager", "admin"]}
