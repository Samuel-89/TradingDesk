"""Configuration and default parameters for TradingDesk."""

from pathlib import Path
from pydantic import BaseModel, Field

# Base directories
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"


class QuantConfig(BaseModel):
    """Quantitative model configuration."""
    risk_free_rate: float = Field(0.045, description="Annualized risk-free interest rate (e.g. 4.5% Treasury)")
    target_dte_min: int = Field(5, description="Minimum days to expiration for options analysis")
    target_dte_max: int = Field(16, description="Maximum days to expiration for nearest weekly options")
    std_dev_multipliers: list[float] = Field(default=[-2.0, -1.0, 0.0, 1.0, 2.0], description="Standard deviation intervals")


class RiskConfig(BaseModel):
    """Risk & compliance officer thresholds."""
    min_option_volume: int = Field(50, description="Minimum ATM option volume threshold for liquidity check")
    min_open_interest: int = Field(100, description="Minimum ATM open interest threshold")
    max_bid_ask_spread_pct: float = Field(0.15, description="Max acceptable bid-ask spread as % of mid price")
    earnings_warning_days: int = Field(14, description="Days before/after earnings to flag high event risk")
    dividend_warning_days: int = Field(7, description="Days before ex-dividend to flag event risk")


class AppConfig(BaseModel):
    """Global TradingDesk application configuration."""
    reports_dir: Path = DEFAULT_REPORTS_DIR
    quant: QuantConfig = Field(default_factory=QuantConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)


config = AppConfig()
