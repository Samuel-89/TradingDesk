"""Risk audit and compliance models."""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class CheckStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class RiskRating(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class VerdictType(str, Enum):
    GO = "GO"
    CAUTION = "CAUTION"
    NO_GO = "NO-GO"


class ChecklistItem(BaseModel):
    name: str
    status: CheckStatus
    detail: str


class RiskAudit(BaseModel):
    """Complete risk audit evaluation."""
    risk_rating: RiskRating
    checklist: List[ChecklistItem]
    bear_case: str = Field(..., description="The 'Bear Case' summary statement")
    worst_case_option_buyer: str = Field(..., description="Max loss for options buyers")
    worst_case_equity_holder: str = Field(..., description="Max drawdown for equity holders")
    suggested_stop_short: float = Field(..., description="Short-term exit price")
    suggested_stop_hard: float = Field(..., description="Hard stop exit price")
    verdict: VerdictType
    verdict_subtitle: str = Field("", description="e.g. Wait for PCE, Avoid Pre-Earnings")
    verdict_rationale: str
