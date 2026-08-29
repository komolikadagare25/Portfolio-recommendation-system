"""
Explains WHY specific sectors and stocks were recommended, using real
data where possible (historical stock volatility via yfinance) and
standard, well-established finance concepts for sectors (defensive vs.
growth sector characterization) rather than invented claims.
"""

import yfinance as yf

from stock_prices import STOCK_TICKER_MAP

# Standard, textbook sector characterization — not derived from live data,
# but well-established finance concepts, stated plainly and honestly.
SECTOR_CHARACTERISTICS = {
    "Banking": (
        "steadier",
        "Banking is generally considered a steadier sector — demand for "
        "financial services holds up even in slower economic periods, "
        "though it can be sensitive to interest rate changes.",
    ),
    "FMCG": (
        "steadier",
        "FMCG (everyday consumer goods) is a classic defensive sector — "
        "people keep buying essentials like food and household products "
        "regardless of the economic climate.",
    ),
    "Utilities": (
        "steadier",
        "Utilities (power, water) provide essential services people need "
        "regardless of the economy, making this one of the steadier "
        "sectors to hold.",
    ),
    "Pharmaceuticals": (
        "steadier",
        "Healthcare demand tends to stay relatively stable even in "
        "downturns, making pharma a traditionally defensive sector.",
    ),
    "IT": (
        "moderate",
        "Established IT services firms tend to be relatively stable, "
        "cash-generative businesses, though they can be affected by "
        "global demand and currency swings.",
    ),
    "Technology": (
        "growth",
        "Technology companies often have higher growth potential but can "
        "see sharper price swings, especially smaller or newer players.",
    ),
    "Renewable Energy": (
        "growth",
        "Renewable energy is a fast-growing but still-maturing industry — "
        "potential for strong long-term growth comes with more "
        "short-term price volatility.",
    ),
    "AI": (
        "growth",
        "AI-related companies are in a high-growth, rapidly-evolving "
        "space — this can mean strong upside, but also more volatility "
        "than established sectors.",
    ),
    "Mid-cap Growth": (
        "growth",
        "Mid-cap companies generally offer higher growth potential than "
        "large, established firms, but with more price volatility along "
        "the way.",
    ),
}


def build_sector_reasoning(sectors: list) -> list:
    result = []
    for sector in sectors:
        info = SECTOR_CHARACTERISTICS.get(sector)
        result.append({
            "sector": sector,
            "character": info[0] if info else None,
            "explanation": info[1] if info else None,
        })
    return result


def _compute_daily_volatility_pct(ticker: str, period: str = "1y") -> float | None:
    """Real historical volatility: the standard deviation of daily
    percentage price changes over the period, as a percentage."""
    try:
        history = yf.Ticker(ticker).history(period=period)
        if history.empty or len(history) < 10:
            return None
        daily_returns = history["Close"].pct_change().dropna()
        return round(float(daily_returns.std() * 100), 2)
    except Exception:
        return None


def _classify_volatility(vol_pct: float) -> str:
    if vol_pct <= 1.5:
        return "Low"
    if vol_pct <= 2.5:
        return "Moderate"
    return "High"


def build_stock_reasoning(stock_names: list) -> list:
    result = []
    for stock_name in stock_names:
        ticker = STOCK_TICKER_MAP.get(stock_name)
        vol_pct = _compute_daily_volatility_pct(ticker) if ticker else None

        if vol_pct is None:
            result.append({
                "stock": stock_name,
                "volatility_pct": None,
                "volatility_label": None,
                "explanation": "Historical volatility data wasn't available for this stock right now.",
            })
            continue

        label = _classify_volatility(vol_pct)
        result.append({
            "stock": stock_name,
            "volatility_pct": vol_pct,
            "volatility_label": label,
            "explanation": (
                f"Over the past year, {stock_name}'s price has moved an average of "
                f"{vol_pct}% per day — {label.lower()} volatility, based on real "
                f"historical price data."
            ),
        })
    return result