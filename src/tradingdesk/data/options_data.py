"""Options chain extraction and strike selection."""

import math
from datetime import datetime, date
from typing import Optional, Dict, Any, Tuple, Sequence
import yfinance as yf
import pandas as pd


def safe_int(val: Any, default: int = 0) -> int:
    """Safely convert value to int handling NaN, None, float strings, and invalid types."""
    try:
        if val is None or pd.isna(val):
            return default
        f = float(val)
        return default if math.isnan(f) else int(f)
    except (ValueError, TypeError):
        return default


def safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to float handling NaN, None, and invalid types."""
    try:
        if val is None or pd.isna(val):
            return default
        f = float(val)
        return default if math.isnan(f) else f
    except (ValueError, TypeError):
        return default


def select_target_expiration(
    expirations: Sequence[str],
    min_dte: int = 5,
    max_dte: int = 16,
    reference_date: Optional[date] = None,
) -> Tuple[Optional[str], int]:
    """Select the nearest suitable expiration date (target weekly expiration, ~8 DTE)."""
    if not expirations:
        return None, 0

    today = reference_date if reference_date is not None else date.today()
    candidates: list[Tuple[str, int]] = []

    for exp_str in expirations:
        try:
            exp_date = datetime.strptime(str(exp_str).strip(), "%Y-%m-%d").date()
            dte = (exp_date - today).days
            if dte >= 1:
                candidates.append((exp_str, dte))
        except ValueError:
            continue

    if not candidates:
        return None, 0

    # Filter within target window
    window_candidates = [c for c in candidates if min_dte <= c[1] <= max_dte]
    if window_candidates:
        # Choose closest to ~8 DTE
        return min(window_candidates, key=lambda x: abs(x[1] - 8))

    # Otherwise return the nearest available expiration > 0 days
    return candidates[0]


def fetch_options_chain_data(symbol: str, spot_price: float) -> Dict[str, Any]:
    """Fetch option chain, identify ATM strike, and extract pricing and volatility."""
    ticker = yf.Ticker(symbol)
    expirations = getattr(ticker, "options", ())

    if not expirations:
        # Fallback for stocks/symbols without options
        return {
            "has_options": False,
            "target_expiration": "N/A",
            "dte": 8,
            "atm_strike": spot_price,
            "atm_call_price": round(spot_price * 0.02, 2),
            "atm_put_price": round(spot_price * 0.02, 2),
            "straddle_price": round(spot_price * 0.04, 2),
            "implied_volatility": 0.25,
            "call_volume": 0,
            "put_volume": 0,
            "call_oi": 0,
            "put_oi": 0,
            "call_bid_ask_spread": 0.0,
            "put_bid_ask_spread": 0.0,
        }

    target_exp, dte = select_target_expiration(expirations)
    if not target_exp:
        target_exp = expirations[0]
        dte = 8

    try:
        chain = ticker.option_chain(target_exp)
        calls: pd.DataFrame = getattr(chain, "calls", pd.DataFrame())
        puts: pd.DataFrame = getattr(chain, "puts", pd.DataFrame())
    except Exception:
        calls = pd.DataFrame()
        puts = pd.DataFrame()

    if calls.empty or puts.empty:
        return {
            "has_options": False,
            "target_expiration": target_exp,
            "dte": dte,
            "atm_strike": spot_price,
            "atm_call_price": round(spot_price * 0.02, 2),
            "atm_put_price": round(spot_price * 0.02, 2),
            "straddle_price": round(spot_price * 0.04, 2),
            "implied_volatility": 0.25,
            "call_volume": 0,
            "put_volume": 0,
            "call_oi": 0,
            "put_oi": 0,
            "call_bid_ask_spread": 0.0,
            "put_bid_ask_spread": 0.0,
        }

    # Find strike closest to spot_price
    calls_df = calls.copy()
    calls_df["strike_diff"] = (calls_df["strike"] - spot_price).abs()
    atm_call_idx = calls_df["strike_diff"].idxmin()
    atm_call = calls_df.loc[atm_call_idx]
    atm_strike = float(atm_call["strike"])

    # Match in puts
    puts_df = puts.copy()
    puts_df["strike_diff"] = (puts_df["strike"] - atm_strike).abs()
    atm_put_idx = puts_df["strike_diff"].idxmin()
    atm_put = puts_df.loc[atm_put_idx]

    # Calculate mid-price or fallback to lastPrice
    def get_option_price(row: pd.Series) -> float:
        bid = safe_float(row.get("bid"))
        ask = safe_float(row.get("ask"))
        if bid > 0 and ask > 0:
            return (bid + ask) / 2.0
        last = safe_float(row.get("lastPrice"))
        return last if last > 0 else 1.0

    call_price = get_option_price(atm_call)
    put_price = get_option_price(atm_put)
    straddle_price = round(call_price + put_price, 2)

    # Implied volatility
    call_iv = safe_float(atm_call.get("impliedVolatility"), 0.25)
    put_iv = safe_float(atm_put.get("impliedVolatility"), 0.25)
    avg_iv = (call_iv + put_iv) / 2.0 if (call_iv > 0 and put_iv > 0) else max(call_iv, put_iv, 0.25)

    # Volume & OI
    call_vol = safe_int(atm_call.get("volume"))
    put_vol = safe_int(atm_put.get("volume"))
    call_oi = safe_int(atm_call.get("openInterest"))
    put_oi = safe_int(atm_put.get("openInterest"))

    # Spreads
    c_bid = safe_float(atm_call.get("bid"))
    c_ask = safe_float(atm_call.get("ask"))
    call_spread = (c_ask - c_bid) if (c_ask > c_bid) else 0.0

    p_bid = safe_float(atm_put.get("bid"))
    p_ask = safe_float(atm_put.get("ask"))
    put_spread = (p_ask - p_bid) if (p_ask > p_bid) else 0.0

    return {
        "has_options": True,
        "target_expiration": target_exp,
        "dte": dte,
        "atm_strike": round(atm_strike, 2),
        "atm_call_price": round(call_price, 2),
        "atm_put_price": round(put_price, 2),
        "straddle_price": straddle_price,
        "implied_volatility": round(avg_iv, 4),
        "call_volume": call_vol,
        "put_volume": put_vol,
        "call_oi": call_oi,
        "put_oi": put_oi,
        "call_bid_ask_spread": round(call_spread, 2),
        "put_bid_ask_spread": round(put_spread, 2),
    }
