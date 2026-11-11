"""Risk checklist evaluations: Liquidity, Event Risk, and Leverage."""

from typing import Dict, Any, Optional
from datetime import datetime, date
import pandas as pd

from tradingdesk.models.risk import ChecklistItem, CheckStatus
from tradingdesk.config import config


def _parse_date(val: Any) -> Optional[date]:
    """Safely parse a date from string, date, datetime, or timestamp."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass

    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val_clean = val.strip()
        if not val_clean:
            return None
        # Try common formats
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%b %d, %Y"):
            try:
                return datetime.strptime(val_clean[:10], "%Y-%m-%d").date()
            except ValueError:
                pass
            try:
                return datetime.strptime(val_clean, fmt).date()
            except ValueError:
                pass
    return None


def evaluate_liquidity(options_meta: Dict[str, Any]) -> ChecklistItem:
    """Check if options volume and open interest provide sufficient liquidity with tight spreads."""
    call_vol = int(options_meta.get("call_volume") or 0)
    put_vol = int(options_meta.get("put_volume") or 0)
    call_oi = int(options_meta.get("call_oi") or 0)
    put_oi = int(options_meta.get("put_oi") or 0)
    call_spread = float(options_meta.get("call_bid_ask_spread") or 0.0)
    put_spread = float(options_meta.get("put_bid_ask_spread") or 0.0)
    spread = max(call_spread, put_spread)
    call_price = float(options_meta.get("atm_call_price") or 1.0)

    spread_pct = (spread / call_price) if call_price > 0 else 0.0

    total_vol = call_vol + put_vol
    total_oi = call_oi + put_oi

    if (
        total_vol >= config.risk.min_option_volume
        and total_oi >= config.risk.min_open_interest
        and spread_pct <= config.risk.max_bid_ask_spread_pct
    ):
        return ChecklistItem(
            name="Liquidity Check",
            status=CheckStatus.PASS,
            detail=f"ATM options show healthy liquidity (Vol: {total_vol}, OI: {total_oi}) with tight bid-ask spreads (${spread:.2f}).",
        )
    elif total_vol > 0:
        return ChecklistItem(
            name="Liquidity Check",
            status=CheckStatus.WARNING,
            detail=f"Moderate liquidity (Vol: {total_vol}, OI: {total_oi}, Spread: ${spread:.2f}). Slippage risk on fast market moves.",
        )
    else:
        return ChecklistItem(
            name="Liquidity Check",
            status=CheckStatus.FAIL,
            detail="Low or zero recorded option volume at ATM strikes. Exit execution may be compromised.",
        )


def evaluate_event_risk(options_meta: Dict[str, Any], extra_meta: Dict[str, Any]) -> ChecklistItem:
    """Check for upcoming earnings calls, dividend dates, or macro events within target DTE."""
    dte = int(options_meta.get("dte") or 8)
    earnings_raw = extra_meta.get("earnings_date")
    dividend_raw = extra_meta.get("dividend_date")

    today = date.today()
    warnings = []

    e_date = _parse_date(earnings_raw)
    if e_date is not None:
        days_to_earnings = (e_date - today).days
        if 0 <= days_to_earnings <= dte:
            warnings.append(
                f"Upcoming earnings release on {e_date.isoformat()} falls directly within the expiration cycle ({dte} DTE)."
            )

    d_date = _parse_date(dividend_raw)
    if d_date is not None:
        days_to_div = (d_date - today).days
        if 0 <= days_to_div <= dte:
            warnings.append(
                f"Ex-dividend date on {d_date.isoformat()} falls within the holding period."
            )

    if warnings:
        return ChecklistItem(
            name="Event Risk",
            status=CheckStatus.FAIL,
            detail="; ".join(warnings) + " Binary event risk creates severe volatility and IV crush exposure.",
        )
    else:
        return ChecklistItem(
            name="Event Risk",
            status=CheckStatus.PASS,
            detail=f"No binary corporate earnings or ex-dividend events detected within the {dte}-day target holding window.",
        )


def evaluate_leverage_risk(straddle_cost: float, spot_price: float) -> ChecklistItem:
    """Assess leverage and max drawdown parameters."""
    cost_pct = (straddle_cost / spot_price) * 100 if spot_price > 0 else 0.0
    if cost_pct > 6.0:
        return ChecklistItem(
            name="Over-Leverage",
            status=CheckStatus.WARNING,
            detail=f"High implied volatility premium ({cost_pct:.1f}% of underlying price). Option buyer requires extreme move to break even.",
        )
    else:
        return ChecklistItem(
            name="Over-Leverage",
            status=CheckStatus.PASS,
            detail=f"ATM straddle premium represents {cost_pct:.1f}% of underlying (${straddle_cost:.2f}/share). Risk is strictly defined for option buyers.",
        )
