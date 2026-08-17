from enum import Enum
from pydantic import BaseModel, Field, field_validator

class Category(str, Enum):
    billing = "billing"
    bug = "bug"
    feature = "feature"
    other = "other"

class Urgency(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"

class TriageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

class TriageResponse(BaseModel):
    category: Category
    urgency: Urgency
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=240)
