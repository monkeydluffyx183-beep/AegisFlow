from typing import Literal

from pydantic import BaseModel, Field


class Disposition(BaseModel):
    disposition: Literal["fraud", "not_fraud", "sar_filed"]
    rationale: str = Field(min_length=10)


class SARApproval(BaseModel):
    rationale: str = Field(min_length=10)


class CaseFilter(BaseModel):
    status: str | None = None
    assigned_to: str | None = None
    sort: Literal["sla", "priority"] = "sla"
