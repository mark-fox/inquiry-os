from __future__ import annotations

from pydantic import BaseModel, Field


class SynthesisOutput(BaseModel):
    summary: str = Field(..., description="Short 3–6 sentence summary.")
    key_points: list[str] = Field(..., description="3–8 key takeaways.")
    risks: list[str] = Field(..., description="Key risks, caveats, or limitations.")
    recommendation: str = Field(..., description="Clear recommendation or next step.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="0.0 to 1.0 confidence score.")