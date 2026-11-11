"""Market data fetcher using yfinance."""

import math
from typing import Optional, Dict, Any, Tuple
import yfinance as yf
import pandas as pd

from tradingdesk.models.market import MarketQuote


def safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """Safely convert value to float, handling NaN, None, and invalid types."""
    try:
        if val is None or pd.isna(val):
            return default
        f = float(val)
        return default if math.isnan(f) else f
    except (ValueError, TypeError):
        return default


def safe_int(val: Any, default: Optional[int] = None) -> Optional[int]:
    """Safely convert value to int, handling NaN, None, float strings, and invalid types."""
    try:
        if val is None or pd.isna(val):
            return default
        f = float(val)
        return default if math.isnan(f) else int(f)
    except (ValueError, TypeError):
        return default


def get_fast_info_val(fast_info: Any, snake_key: str, camel_key: str, default: Any = None) -> Any:
    """Safely get values from yfinance fast_info across attributes and dictionary keys."""
    if fast_info is None:
        return default

    # Try attribute access (snake_case then camelCase)
    for key in (snake_key, camel_key):
        try:
            val = getattr(fast_info, key, None)
            if val is not None and not pd.isna(val):
                return val
        except Exception:
            pass

    # Try indexing / get access (snake_case then camelCase)
    for key in (snake_key, camel_key):
        try:
            if hasattr(fast_info, "get"):
                val = fast_info.get(key)
                if val is not None and not pd.isna(val):
                    return val
            elif hasattr(fast_info, "__getitem__"):
                val = fast_info[key]
                if val is not None and not pd.isna(val):
                    return val
        except Exception:
            pass

    return default


def fetch_market_quote(symbol: str) -> Tuple[MarketQuote, Dict[str, Any]]:
    """Fetch live market quote, statistics, and calendar dates for a ticker symbol."""
    ticker = yf.Ticker(symbol)
    fast_info = getattr(ticker, "fast_info", None)

    raw_last = get_fast_info_val(fast_info, "last_price", "lastPrice", 0.0)
    last_price = safe_float(raw_last, 0.0) or 0.0

    raw_high = get_fast_info_val(fast_info, "day_high", "dayHigh", last_price)
    day_high = safe_float(raw_high, last_price) or last_price

    raw_low = get_fast_info_val(fast_info, "day_low", "dayLow", last_price)
    day_low = safe_float(raw_low, last_price) or last_price

    raw_prev = get_fast_info_val(fast_info, "previous_close", "previousClose", last_price)
    prev_close = safe_float(raw_prev, last_price) or last_price

    raw_vol = get_fast_info_val(fast_info, "last_volume", "lastVolume", None)
    volume = safe_int(raw_vol)

    fifty_two_week_high = safe_float(get_fast_info_val(fast_info, "year_high", "yearHigh", None))
    fifty_two_week_low = safe_float(get_fast_info_val(fast_info, "year_low", "yearLow", None))

    # Fetch extra company info and calendar safely
    extra_meta: Dict[str, Any] = {}
    company_name = symbol.upper()
    beta = None
    sector = None
    industry = None
    pe_ratio = None

    try:
        info = getattr(ticker, "info", None)
        if info and isinstance(info, dict):
            company_name = info.get("shortName") or info.get("longName") or company_name
            beta = safe_float(info.get("beta"))
            sector = info.get("sector")
            industry = info.get("industry")
            pe_ratio = safe_float(info.get("trailingPE") or info.get("forwardPE"))
            if fifty_two_week_high is None:
                fifty_two_week_high = safe_float(info.get("fiftyTwoWeekHigh"))
            if fifty_two_week_low is None:
                fifty_two_week_low = safe_float(info.get("fiftyTwoWeekLow"))
            extra_meta["target_mean_price"] = safe_float(info.get("targetMeanPrice"))
            extra_meta["recommendation_key"] = info.get("recommendationKey")
            extra_meta["earnings_growth"] = safe_float(info.get("earningsGrowth"))
    except Exception:
        pass

    # Calendar dates (earnings, dividend)
    earnings_date_str = None
    dividend_date_str = None
    try:
        cal = getattr(ticker, "calendar", None)
        if cal is not None:
            if isinstance(cal, dict):
                e_date = cal.get("Earnings Date")
                if e_date:
                    val = e_date[0] if isinstance(e_date, (list, tuple)) and len(e_date) > 0 else e_date
                    earnings_date_str = str(val)
                d_date = cal.get("Ex-Dividend Date") or cal.get("Dividend Date")
                if d_date:
                    dividend_date_str = str(d_date)
            elif hasattr(cal, "to_dict"):
                cal_dict = cal.to_dict()
                extra_meta["calendar_raw"] = cal_dict
                if "Earnings Date" in cal_dict:
                    val = cal_dict["Earnings Date"]
                    if isinstance(val, dict):
                        first_val = next(iter(val.values()), None)
                        if first_val:
                            earnings_date_str = str(first_val)
                    else:
                        earnings_date_str = str(val)
                if "Ex-Dividend Date" in cal_dict or "Dividend Date" in cal_dict:
                    d_val = cal_dict.get("Ex-Dividend Date") or cal_dict.get("Dividend Date")
                    if isinstance(d_val, dict):
                        first_d = next(iter(d_val.values()), None)
                        if first_d:
                            dividend_date_str = str(first_d)
                    else:
                        dividend_date_str = str(d_val)
    except Exception:
        pass

    extra_meta["earnings_date"] = earnings_date_str
    extra_meta["dividend_date"] = dividend_date_str

    quote = MarketQuote(
        symbol=symbol.upper(),
        company_name=company_name,
        last_price=round(last_price, 2),
        day_high=round(day_high, 2),
        day_low=round(day_low, 2),
        previous_close=round(prev_close, 2),
        volume=volume,
        fifty_two_week_high=round(fifty_two_week_high, 2) if fifty_two_week_high is not None else None,
        fifty_two_week_low=round(fifty_two_week_low, 2) if fifty_two_week_low is not None else None,
        beta=round(beta, 2) if beta is not None else None,
        pe_ratio=round(pe_ratio, 2) if pe_ratio is not None else None,
        sector=sector,
        industry=industry,
    )

    return quote, extra_meta
