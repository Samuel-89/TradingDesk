"""Black-Scholes-Merton analytical formulas for options pricing and Greeks."""

import math
from typing import Tuple
from scipy.stats import norm

from tradingdesk.models.options import Greeks


def calc_d1_d2(
    spot: float, strike: float, time_to_exp: float, risk_free_rate: float, sigma: float
) -> Tuple[float, float]:
    """Calculate d1 and d2 terms in Black-Scholes.

    Parameters:
        spot: Underlying stock price (S)
        strike: Strike price (K)
        time_to_exp: Time to expiration in years (T)
        risk_free_rate: Annualized risk-free interest rate (r)
        sigma: Implied volatility (sigma)
    """
    if spot <= 0 or strike <= 0 or time_to_exp <= 0 or sigma <= 0:
        return 0.0, 0.0

    sqrt_t = math.sqrt(time_to_exp)
    d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * sigma**2) * time_to_exp) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    return d1, d2


def calculate_greeks(
    spot: float,
    strike: float,
    time_to_exp_years: float,
    risk_free_rate: float,
    sigma: float,
) -> Greeks:
    """Calculate analytical Black-Scholes Greeks for Call, Put, and Straddle.

    Parameters:
        spot: Underlying stock price
        strike: Option strike price (ATM)
        time_to_exp_years: Time to expiration in years (DTE / 365.0)
        risk_free_rate: Annualized risk-free interest rate (decimal, e.g. 0.045)
        sigma: Implied volatility (decimal, e.g. 0.259 for 25.9%)
    """
    if spot <= 0 or strike <= 0 or time_to_exp_years <= 0 or sigma <= 0:
        return Greeks(
            delta_call=0.50,
            delta_put=-0.50,
            gamma=0.0,
            theta_call=0.0,
            theta_put=0.0,
            theta_straddle=0.0,
            vega=0.0,
        )

    sqrt_t = math.sqrt(time_to_exp_years)
    d1, d2 = calc_d1_d2(spot, strike, time_to_exp_years, risk_free_rate, sigma)

    # Standard normal CDF and PDF
    n_d1 = norm.cdf(d1)
    n_d2 = norm.cdf(d2)
    n_minus_d2 = norm.cdf(-d2)
    pdf_d1 = norm.pdf(d1)

    # Delta
    delta_call = float(n_d1)
    delta_put = float(n_d1 - 1.0)

    # Gamma (identical for Call and Put)
    gamma = float(pdf_d1 / (spot * sigma * sqrt_t))

    # Theta (annualized converted to per calendar day / 365)
    exp_factor = math.exp(-risk_free_rate * time_to_exp_years)
    common_term = -(spot * pdf_d1 * sigma) / (2.0 * sqrt_t)

    theta_call_annual = common_term - (risk_free_rate * strike * exp_factor * n_d2)
    theta_put_annual = common_term + (risk_free_rate * strike * exp_factor * n_minus_d2)

    theta_call_daily = float(theta_call_annual / 365.0)
    theta_put_daily = float(theta_put_annual / 365.0)
    theta_straddle_daily = float(theta_call_daily + theta_put_daily)

    # Vega (dollar change per 1 percentage point change in IV -> multiply by 0.01)
    vega_1pct = float(spot * sqrt_t * pdf_d1 * 0.01)

    return Greeks(
        delta_call=round(delta_call, 2),
        delta_put=round(delta_put, 2),
        gamma=round(gamma, 4),
        theta_call=round(theta_call_daily, 2),
        theta_put=round(theta_put_daily, 2),
        theta_straddle=round(theta_straddle_daily, 2),
        vega=round(vega_1pct, 2),
    )
