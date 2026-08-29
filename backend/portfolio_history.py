"""
Builds a real, historical (not predicted) performance view of a user's
whole portfolio, using actual market data via yfinance:
  - Stocks: the user's actual recommended stocks, equally weighted.
  - Mutual Funds: no specific fund is recommended anywhere in this app,
    so the Nifty 50 index is used as a clearly-labeled proxy for "a fund
    tracking the broad market" — real data, explicitly disclosed as a
    stand-in, not the literal product a user would buy.
  - Gold: GOLDBEES.NS (Nippon India ETF Gold BeES), a real, liquid,
    NSE-listed gold ETF.
  - Government Bonds & Fixed Deposits: intentionally excluded — there is
    no honest market-linked historical price series for these without
    inventing a number, which this module will not do. Their combined
    percentage is reported separately as "not shown".
"""

import pandas as pd
import yfinance as yf

from stock_prices import STOCK_TICKER_MAP

NIFTY_TICKER = "^NSEI"
GOLD_TICKER = "GOLDBEES.NS"

CATEGORY_TICKERS = {
    "Mutual Funds": NIFTY_TICKER,
    "Gold": GOLD_TICKER,
}

EXCLUDED_CATEGORIES = {"Government Bonds", "Fixed Deposits"}


def _fetch_close_series(ticker: str, period: str) -> pd.Series | None:
    try:
        history = yf.Ticker(ticker).history(period=period)
        if history.empty:
            return None
        return history["Close"]
    except Exception:
        return None


def _normalize(series: pd.Series) -> pd.Series:
    """Rescales a price series so it starts at 100 — makes differently
    priced assets comparable on the same chart."""
    return series / series.iloc[0] * 100


def build_portfolio_history(
    asset_allocation: dict,
    recommended_stocks: list,
    period: str = "1y",
    invested_amount: float = 10000.0,
) -> dict:
    category_series = {}

    # Stocks: equal-weighted average of the user's actual recommended stocks.
    if "Stocks" in asset_allocation and recommended_stocks:
        stock_series_list = []
        for stock_name in recommended_stocks:
            ticker = STOCK_TICKER_MAP.get(stock_name)
            if not ticker:
                continue
            series = _fetch_close_series(ticker, period)
            if series is not None and len(series) > 1:
                stock_series_list.append(_normalize(series))

        if stock_series_list:
            combined = pd.concat(stock_series_list, axis=1, join="inner")
            category_series["Stocks"] = combined.mean(axis=1)

    # Mutual Funds (Nifty 50 proxy) and Gold.
    for category, ticker in CATEGORY_TICKERS.items():
        if category in asset_allocation:
            series = _fetch_close_series(ticker, period)
            if series is not None and len(series) > 1:
                category_series[category] = _normalize(series)

    if not category_series:
        return {
            "dates": [],
            "portfolio_values": [],
            "included_categories": {},
            "excluded_pct": sum(asset_allocation.get(c, 0) for c in EXCLUDED_CATEGORIES),
            "start_pct_change": None,
            "note": "Live historical market data was unavailable for this portfolio right now.",
        }

    # Align all included series on their common trading dates.
    aligned = pd.concat(category_series.values(), axis=1, join="inner")
    aligned.columns = list(category_series.keys())
    aligned = aligned.resample("W").last().dropna()

    included_pct_total = sum(asset_allocation.get(c, 0) for c in category_series)
    weights = {c: asset_allocation.get(c, 0) / included_pct_total for c in category_series}

    portfolio_index = sum(aligned[c] * weights[c] for c in category_series)  # normalized, starts at 100

    excluded_pct = sum(asset_allocation.get(c, 0) for c in EXCLUDED_CATEGORIES)
    included_amount = invested_amount * (included_pct_total / 100)

    rupee_values = portfolio_index / 100 * included_amount

    start_val = float(rupee_values.iloc[0])
    end_val = float(rupee_values.iloc[-1])
    pct_change = round((end_val - start_val) / start_val * 100, 2)

    return {
        "dates": [d.strftime("%Y-%m-%d") for d in rupee_values.index],
        "portfolio_values": [round(float(v), 2) for v in rupee_values.values],
        "included_categories": {c: round(w * included_pct_total, 1) for c, w in weights.items()},
        "excluded_pct": round(excluded_pct, 1),
        "invested_amount": invested_amount,
        "included_amount": round(included_amount, 2),
        "start_value": round(start_val, 2),
        "end_value": round(end_val, 2),
        "start_pct_change": pct_change,
        "note": (
            "Mutual Funds is represented by the Nifty 50 index as a proxy, since no specific fund "
            "is recommended. This shows real historical performance, not a prediction or guarantee "
            "of future returns."
        ),
    }