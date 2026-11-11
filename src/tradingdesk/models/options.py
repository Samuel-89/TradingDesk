"""Options and quantitative calculation models."""

from typing import List
from pydantic import BaseModel, Field


class Greeks(BaseModel):
    """First and second-order option Greeks for ATM options."""
    delta_call: float = Field(..., description="ATM Call Delta")
    delta_put: float = Field(..., description="ATM Put Delta")
    gamma: float = Field(..., description="ATM Option Gamma")
    theta_call: float = Field(..., description="Daily theta decay for ATM Call ($/day)")
    theta_put: float = Field(..., description="Daily theta decay for ATM Put ($/day)")
    theta_straddle: float = Field(..., description="Combined ATM Straddle daily theta ($/day)")
    vega: float = Field(..., description="Option Vega per 1% change in IV")


class ExpectedMove(BaseModel):
    """1-Standard Deviation expected move calculations."""
    target_expiration: str = Field(..., description="Expiration date (YYYY-MM-DD)")
    dte: int = Field(..., description="Days to expiration")
    implied_volatility: float = Field(..., description="Annualized implied volatility (as % or decimal)")
    expected_move_dollar: float = Field(..., description="1-SD dollar move (±$)")
    range_low: float = Field(..., description="Lower 1-SD price bound")
    range_high: float = Field(..., description="Upper 1-SD price bound")


class PnLRow(BaseModel):
    """A row in the hypothetical ATM Straddle P/L table."""
    scenario_label: str = Field(..., description="e.g. -2 SD, -1 SD, ATM, +1 SD, +2 SD")
    underlying_price: float = Field(..., description="Underlying price at expiration")
    pnl_per_share: float = Field(..., description="P/L at expiration per share ($)")


class OptionsAnalysis(BaseModel):
    """Full quantitative options review."""
    atm_strike: float
    atm_call_price: float
    atm_put_price: float
    straddle_cost: float
    expected_move: ExpectedMove
    greeks: Greeks
    pnl_table: List[PnLRow]
