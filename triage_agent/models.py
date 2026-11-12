from pydantic import BaseModel, Field


class InvestigationPlan(BaseModel):
    search_terms: list[str] = Field(description="Short terms useful for finding relevant logs and source")
    continue_investigation: bool = Field(description="Whether another evidence-gathering round may help")


class Finding(BaseModel):
    title: str
    summary: str
    severity: str = Field(description="One of critical, high, medium, low")
    priority: int = Field(description="ClickUp priority: 1 urgent, 2 high, 3 normal, 4 low")
    evidence: list[str]
    suggested_next_step: str
