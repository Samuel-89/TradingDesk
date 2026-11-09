"""Market data models."""

from typing import Optional
from pydantic import BaseModel


class MarketQuote(BaseModel):
    """Underlying equity quote and core statistical metrics."""
    symbol: str
    company_name: str = ""
    last_price: float
    day_high: float
    day_low: float
    previous_close: float
    volume: Optional[int] = None
    avg_volume_10d: Optional[int] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    beta: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    dividend_yield: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
