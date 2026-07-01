"""
Download historical stock data from Yahoo Finance
and save each stock as a CSV file.
"""

from pathlib import Path
import yfinance as yf

# -------------------------------
# List of Indian Stocks
# -------------------------------
STOCKS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "ITC.NS",
    "LT.NS",
    "BHARTIARTL.NS",
    "WIPRO.NS"
]

# -------------------------------
# Project Paths
# -------------------------------
# download_data.py
#      ↑
#     src
#      ↑
#      ml
BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = BASE_DIR / "data" / "raw"

# Create folder if it doesn't exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------
# Download Function
# -------------------------------
def download_stock_data(ticker):
    """
    Downloads 5 years of historical stock data
    and saves it as a CSV file.
    """

    print(f"\nDownloading {ticker}...")

    df = yf.download(
        ticker,
        period="5y",
        auto_adjust=False,
        progress=False
    )

    if df.empty:
        print(f"❌ No data found for {ticker}")
        return

    # Convert RELIANCE.NS -> RELIANCE_NS.csv
    filename = ticker.replace(".", "_") + ".csv"

    filepath = RAW_DATA_DIR / filename

    print("Saving to:", filepath)

    df.to_csv(filepath)

    print(f"✅ Saved {filename}")


# -------------------------------
# Main Program
# -------------------------------
if __name__ == "__main__":

    print("=" * 50)
    print("Downloading Indian Stock Data")
    print("=" * 50)

    for stock in STOCKS:
        download_stock_data(stock)

    print("\n🎉 All downloads completed successfully!")