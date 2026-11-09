"""Complete Trading Desk review report model."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from tradingdesk.models.market import MarketQuote
from tradingdesk.models.options import OptionsAnalysis
from tradingdesk.models.risk import RiskAudit


class MarketResearch(BaseModel):
    """Market research and offline sentiment evaluation."""
    sentiment: str = Field("Neutral", description="e.g. Bullish / Moderate Buy, Bearish")
    summary: str
    key_headlines: List[str] = Field(default_factory=list)
    earnings_date: Optional[str] = None
    dividend_date: Optional[str] = None


class DeskReport(BaseModel):
    """The unified multi-role Trading Desk report."""
    symbol: str
    date_str: str = Field(default_factory=lambda: datetime.now().strftime("%B %d, %Y"))
    market_quote: MarketQuote
    research: MarketResearch
    quant: OptionsAnalysis
    risk: RiskAudit
