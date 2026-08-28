"""
Fetches live stock prices via yfinance and maps our recommended stock
display names (from ml/portfolio/src/portfolio_recommender.py) to their
NSE ticker symbols. Kept separate from the ML module itself — this is
our own integration layer, not part of the ML pipeline.
"""

import yfinance as yf

STOCK_TICKER_MAP = {
    "TCS": "TCS.NS",
    "Infosys": "INFY.NS",
    "Wipro": "WIPRO.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "SBI": "SBIN.NS",
    "Sun Pharma": "SUNPHARMA.NS",
    "Cipla": "CIPLA.NS",
    "Dr. Reddy's": "DRREDDY.NS",
    "ITC": "ITC.NS",
    "Hindustan Unilever": "HINDUNILVR.NS",
    "Nestle India": "NESTLEIND.NS",
    "NTPC": "NTPC.NS",
    "Power Grid": "POWERGRID.NS",
    "LTIMindtree": "LTIM.NS",
    "Tata Power": "TATAPOWER.NS",
    "Adani Green": "ADANIGREEN.NS",
    "Suzlon": "SUZLON.NS",
    "Tata Elxsi": "TATAELXSI.NS",
    "Persistent Systems": "PERSISTENT.NS",
    "Dixon Technologies": "DIXON.NS",
    "Polycab": "POLYCAB.NS",
    "Astral": "ASTRAL.NS",
}


def get_live_price(stock_name: str) -> float | None:
    """Returns the latest closing price for a stock, or None if it can't
    be fetched (unknown ticker, network issue, market data unavailable)."""
    ticker_symbol = STOCK_TICKER_MAP.get(stock_name)
    if not ticker_symbol:
        return None
    try:
        history = yf.Ticker(ticker_symbol).history(period="1d")
        if history.empty:
            return None
        return float(history["Close"].iloc[-1])
    except Exception:
        return None


def build_investment_plan(total_amount: float, asset_allocation: dict, recommended_stocks: list) -> dict:
    """Splits total_amount across asset categories per asset_allocation
    percentages, then breaks the Stocks category down into equal-weighted
    share purchases using live prices."""
    category_amounts = {
        category: round(total_amount * pct / 100, 2)
        for category, pct in asset_allocation.items()
    }

    stocks_amount = category_amounts.get("Stocks", 0)
    stock_plan = []

    if recommended_stocks:
        per_stock_amount = stocks_amount / len(recommended_stocks)
        for stock_name in recommended_stocks:
            price = get_live_price(stock_name)
            if price is None or price <= 0:
                stock_plan.append({
                    "stock": stock_name,
                    "allocated_amount": round(per_stock_amount, 2),
                    "price": None,
                    "shares": None,
                    "invested_amount": None,
                    "leftover": None,
                    "error": "Live price unavailable",
                })
                continue

            shares = int(per_stock_amount // price)
            invested = round(shares * price, 2)
            leftover = round(per_stock_amount - invested, 2)

            stock_plan.append({
                "stock": stock_name,
                "allocated_amount": round(per_stock_amount, 2),
                "price": round(price, 2),
                "shares": shares,
                "invested_amount": invested,
                "leftover": leftover,
                "error": None,
            })

    return {
        "total_amount": total_amount,
        "category_amounts": category_amounts,
        "stock_plan": stock_plan,
    }