"""Download raw historical stock data from Yahoo Finance.

This module is the data-acquisition entry point for the Explainable
AI-Based Portfolio Recommendation System. Its sole responsibility is
to fetch historical OHLCV data for a configured list of Indian (NSE)
stocks and persist it, unmodified, as CSV files under ``ml/data/raw/``.

This module MUST NOT:
    * Clean, impute, or otherwise transform the downloaded data.
    * Perform feature engineering.
    * Perform exploratory data analysis or plotting.
    * Train or evaluate any model.

Those responsibilities belong to later stages of the pipeline
(``clean_data.py``, ``feature_engineering.py``, and beyond).

Typical usage:
    python -m src.download_data
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------
import logging
from pathlib import Path
from typing import Final, Optional

import pandas as pd
import yfinance as yf

# ----------------------------------------------------------------------------
# Configuration / Constants
# ----------------------------------------------------------------------------
# Centralizing configuration here means that swapping data providers,
# adjusting the download window, or pointing at a different storage
# location never requires touching the functions below -- only the
# values in this section.

#: Download window passed to yfinance (e.g. "1y", "5y", "max").
DOWNLOAD_PERIOD: Final[str] = "5y"

#: Whether yfinance should auto-adjust OHLC values for splits/dividends.
#: Kept False so the raw data is exactly what Yahoo Finance returns.
AUTO_ADJUST: Final[bool] = False

#: Whether yfinance should print its own progress bar.
SHOW_PROGRESS: Final[bool] = False

#: Columns that must be present for a downloaded DataFrame to be
#: considered valid/usable.
REQUIRED_COLUMNS: Final[tuple] = ("Open", "High", "Low", "Close", "Volume")

#: NSE ticker symbols to download. Yahoo Finance requires the ".NS"
#: suffix for National Stock Exchange of India listings.
STOCK_LIST: Final[list] = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "ITC.NS",
    "LT.NS",
    "BHARTIARTL.NS",
    "WIPRO.NS",
]

# ml/src/download_data.py -> parent (src) -> parent (ml)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Directory where raw, unmodified CSV files are stored.
RAW_DATA_DIR: Final[Path] = BASE_DIR / "data" / "raw"

#: Logging verbosity for this module. One of the standard levels
#: defined in the `logging` module (e.g. logging.INFO, logging.DEBUG).
LOG_LEVEL: Final[int] = logging.INFO

# ----------------------------------------------------------------------------
# Logger
# ----------------------------------------------------------------------------
# A module-level, named logger is used instead of the root logger so
# that downstream code (e.g. a future pipeline orchestrator) can
# configure, filter, or redirect this module's logs independently of
# other modules' logs.
logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Attach a basic stream handler to this module's logger.

    This is intentionally minimal and only applied when the module is
    run as a script (see the entry point at the bottom of the file).
    Library-style usage (``from src.download_data import ...``) should
    not have logging handlers forced onto it by the importing code.
    """
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(LOG_LEVEL)


# ----------------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------------
def _ticker_to_filename(ticker: str) -> str:
    """Convert a Yahoo Finance ticker symbol into a safe CSV filename.

    Args:
        ticker: A Yahoo Finance ticker symbol, e.g. ``"RELIANCE.NS"``.

    Returns:
        A filesystem-safe filename, e.g. ``"RELIANCE_NS.csv"``.
    """
    return ticker.replace(".", "_") + ".csv"


def _log_download_metadata(ticker: str, df: pd.DataFrame, saved_path: Path) -> None:
    """Log summary metadata for a successfully downloaded stock.

    Args:
        ticker: The ticker symbol that was downloaded.
        df: The validated DataFrame that was saved.
        saved_path: The path the DataFrame was written to.
    """
    start_date = df.index.min()
    end_date = df.index.max()
    logger.info(
        "Downloaded %s | Rows: %d | Columns: %d | Date range: %s -> %s | Saved: %s",
        ticker,
        df.shape[0],
        df.shape[1],
        start_date.date() if hasattr(start_date, "date") else start_date,
        end_date.date() if hasattr(end_date, "date") else end_date,
        saved_path,
    )


# ----------------------------------------------------------------------------
# Core Functions
# ----------------------------------------------------------------------------
def download_stock(ticker: str) -> pd.DataFrame:
    """Download historical OHLCV data for a single ticker.

    This is the only function that talks to an external data
    provider. Swapping Yahoo Finance for another provider (Alpha
    Vantage, Polygon, an NSE API, etc.) in the future should only
    require changing the implementation of this function -- every
    other function in this module is provider-agnostic.

    Args:
        ticker: A Yahoo Finance ticker symbol, e.g. ``"RELIANCE.NS"``.

    Returns:
        The raw DataFrame returned by the data provider. May be empty
        if the provider returned no data; callers must not assume the
        result is usable without calling `validate_download` first.

    Raises:
        Exception: Any exception raised by the underlying data
            provider client (e.g. network errors) is propagated to
            the caller, which is expected to catch and log it so that
            one failing ticker does not halt the whole run.
    """
    logger.debug("Requesting data for %s from Yahoo Finance", ticker)
    df = yf.download(
        ticker,
        period=DOWNLOAD_PERIOD,
        auto_adjust=AUTO_ADJUST,
        progress=SHOW_PROGRESS,
    )
    return df


def validate_download(ticker: str, df: pd.DataFrame) -> bool:
    """Verify that a downloaded DataFrame is usable before saving.

    This function performs *validation only*. It never mutates,
    cleans, imputes, or otherwise modifies the DataFrame -- data
    cleaning is explicitly out of scope for this module.

    Checks performed:
        * The DataFrame is not empty.
        * The DataFrame has at least one row.
        * All of `REQUIRED_COLUMNS` are present.

    Args:
        ticker: The ticker symbol the DataFrame belongs to (used only
            for logging context).
        df: The DataFrame returned by `download_stock`.

    Returns:
        True if the DataFrame passes all checks and is safe to save,
        False otherwise.
    """
    if df is None or df.empty:
        logger.warning("No data returned for %s; skipping.", ticker)
        return False

    if df.shape[0] == 0:
        logger.warning("Zero rows returned for %s; skipping.", ticker)
        return False

    # yfinance can return a MultiIndex column structure when downloading
    # a single ticker with certain versions/configurations. Flatten the
    # top level for the purposes of column-presence validation only;
    # this check does not alter the DataFrame that gets saved.
    columns = df.columns.get_level_values(0) if isinstance(df.columns, pd.MultiIndex) else df.columns
    missing_columns = set(REQUIRED_COLUMNS) - set(columns)

    if missing_columns:
        logger.warning(
            "Missing required columns %s for %s; skipping.",
            sorted(missing_columns),
            ticker,
        )
        return False

    return True


def save_stock(ticker: str, df: pd.DataFrame) -> Path:
    """Persist a validated DataFrame as a raw CSV file.

    Args:
        ticker: The ticker symbol the DataFrame belongs to.
        df: A DataFrame that has already passed `validate_download`.

    Returns:
        The path the CSV file was written to. Returning this value
        (rather than None) makes it easy for downstream modules --
        e.g. a future pipeline orchestrator or `clean_data.py` -- to
        chain directly off of this function's result.
    """
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = RAW_DATA_DIR / _ticker_to_filename(ticker)
    df.to_csv(filepath)
    return filepath


def process_stock(ticker: str) -> Optional[Path]:
    """Run the full download -> validate -> save flow for one ticker.

    Any exception raised while downloading is caught and logged as an
    error so that a single failing ticker (e.g. due to a network
    issue or an invalid symbol) never halts the rest of the run.

    Args:
        ticker: A Yahoo Finance ticker symbol, e.g. ``"RELIANCE.NS"``.

    Returns:
        The path the CSV file was saved to, or None if the download
        failed or the data did not pass validation.
    """
    try:
        df = download_stock(ticker)
    except Exception:
        logger.error("Failed to download %s", ticker, exc_info=True)
        return None

    if not validate_download(ticker, df):
        return None

    saved_path = save_stock(ticker, df)
    _log_download_metadata(ticker, df, saved_path)
    return saved_path


# ----------------------------------------------------------------------------
# Main Function
# ----------------------------------------------------------------------------
def main() -> None:
    """Download and save raw data for every ticker in `STOCK_LIST`.

    Iterates over all configured tickers, processing each
    independently via `process_stock` so that failures are isolated
    per-ticker rather than aborting the entire run.
    """
    logger.info("Starting raw data download for %d tickers.", len(STOCK_LIST))

    succeeded = 0
    failed = 0

    for ticker in STOCK_LIST:
        result = process_stock(ticker)
        if result is not None:
            succeeded += 1
        else:
            failed += 1

    logger.info(
        "Download run complete. Succeeded: %d | Failed: %d | Output dir: %s",
        succeeded,
        failed,
        RAW_DATA_DIR,
    )


# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    _configure_logging()
    main()