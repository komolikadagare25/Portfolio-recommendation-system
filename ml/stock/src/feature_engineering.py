"""Engineer baseline features from cleaned stock data.

This module is the feature-engineering stage of the Explainable
AI-Based Portfolio Recommendation System pipeline. Its sole
responsibility is to compute a first, baseline set of return, trend,
volatility, and calendar features from the standardized data in
``ml/data/interim/`` and persist the result to ``ml/data/features/``.

Only the following features are implemented in this version:
    * Daily Return
    * Log Return
    * SMA 20 / SMA 50
    * EMA 12 / EMA 26
    * 30-day Rolling Volatility
    * Month / Quarter / Day of Week

This module MUST NOT:
    * Compute RSI, MACD, Bollinger Bands, ATR, or OBV.
    * Compute Sharpe Ratio, Beta, or Maximum Drawdown.
    * Perform feature selection.
    * Train, evaluate, or explain (SHAP/LIME) any model.

Those responsibilities belong to later iterations/stages of the
pipeline.

Typical usage:
    python -m src.feature_engineering
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------
import logging
from pathlib import Path
from typing import Final, Optional

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# Configuration / Constants
# ----------------------------------------------------------------------------
# ml/src/feature_engineering.py -> parent (src) -> parent (ml)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Directory containing cleaned, standardized CSV files from clean_data.py.
INTERIM_DATA_DIR: Final[Path] = BASE_DIR / "data" / "interim"

#: Directory where engineered feature CSV files are written.
FEATURES_DATA_DIR: Final[Path] = BASE_DIR / "data" / "features"

#: Price column used as the basis for return, trend, and volatility features.
PRICE_COLUMN: Final[str] = "Adj Close"

#: Window sizes (in trading days) for Simple Moving Average features.
SMA_WINDOWS: Final[tuple] = (20, 50)

#: Spans (in trading days) for Exponential Moving Average features.
EMA_SPANS: Final[tuple] = (12, 26)

#: Window size (in trading days) for rolling volatility.
VOLATILITY_WINDOW: Final[int] = 30

#: Columns that must be present in the input data for processing to proceed.
REQUIRED_COLUMNS: Final[tuple] = ("Date", "Open", "High", "Low", "Close", "Adj Close", "Volume")

#: Logging verbosity for this module.
LOG_LEVEL: Final[int] = logging.INFO

# ----------------------------------------------------------------------------
# Logger
# ----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Attach a basic stream handler to this module's logger.

    Applied only when the module is run as a script (see the entry
    point at the bottom of the file), so importing this module does
    not silently attach handlers to a caller's logging configuration.
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
def _validate_input_columns(ticker: str, df: pd.DataFrame) -> bool:
    """Verify that a loaded DataFrame has all columns required for feature engineering.

    Args:
        ticker: The ticker symbol (used only for logging context).
        df: A DataFrame as returned by `load_stock_data`.

    Returns:
        True if every column in `REQUIRED_COLUMNS` is present and the
        DataFrame is non-empty, False otherwise.
    """
    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)

    if missing_columns:
        logger.warning(
            "Missing required columns %s for %s; skipping.",
            sorted(missing_columns),
            ticker,
        )
        return False

    if df.empty:
        logger.warning("No data rows found for %s; skipping.", ticker)
        return False

    return True


def _log_feature_metadata(ticker: str, df: pd.DataFrame, saved_path: Path) -> None:
    """Log summary metadata for a successfully engineered feature set.

    Args:
        ticker: The ticker symbol that was processed.
        df: The final DataFrame that was saved.
        saved_path: The path the DataFrame was written to.
    """
    logger.info(
        "Engineered features for %s | Rows: %d | Columns: %d | Saved: %s",
        ticker,
        df.shape[0],
        df.shape[1],
        saved_path,
    )


# ----------------------------------------------------------------------------
# Core Functions
# ----------------------------------------------------------------------------
def load_stock_data(filepath: Path) -> pd.DataFrame:
    """Load a single cleaned stock CSV file produced by clean_data.py.

    Args:
        filepath: Path to a cleaned CSV file in `INTERIM_DATA_DIR`.

    Returns:
        The cleaned DataFrame with the Date column parsed as datetime.
    """
    logger.debug("Loading interim file: %s", filepath)
    return pd.read_csv(filepath, parse_dates=["Date"])


def calculate_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Add Daily Return and Log Return columns.

    Daily Return is the simple percentage change of `PRICE_COLUMN`.
    Log Return is the natural log of the ratio between consecutive
    `PRICE_COLUMN` values. Both are standard, non-overlapping ways of
    expressing period-over-period price change.

    Args:
        df: A DataFrame with at least `PRICE_COLUMN`, sorted by Date.

    Returns:
        A new DataFrame with `Daily Return` and `Log Return` columns
        appended.
    """
    result = df.copy()
    result["Daily Return"] = result[PRICE_COLUMN].pct_change()
    result["Log Return"] = np.log(result[PRICE_COLUMN] / result[PRICE_COLUMN].shift(1))
    return result


def calculate_trend_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add Simple Moving Average and Exponential Moving Average columns.

    Adds one SMA column per window in `SMA_WINDOWS` and one EMA column
    per span in `EMA_SPANS`, all computed on `PRICE_COLUMN`.

    Args:
        df: A DataFrame with at least `PRICE_COLUMN`, sorted by Date.

    Returns:
        A new DataFrame with `SMA_{window}` and `EMA_{span}` columns
        appended.
    """
    result = df.copy()

    for window in SMA_WINDOWS:
        result[f"SMA_{window}"] = result[PRICE_COLUMN].rolling(window=window).mean()

    for span in EMA_SPANS:
        result[f"EMA_{span}"] = result[PRICE_COLUMN].ewm(span=span, adjust=False).mean()

    return result


def calculate_volatility_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add a rolling volatility column based on Daily Return.

    Rolling volatility is the rolling standard deviation of `Daily
    Return` over `VOLATILITY_WINDOW` trading days. Requires `Daily
    Return` to already exist (see `calculate_returns`).

    Args:
        df: A DataFrame that already has a `Daily Return` column.

    Returns:
        A new DataFrame with a `Rolling Volatility` column appended.

    Raises:
        KeyError: If `Daily Return` is not present, surfaced to the
            caller so `process_stock` can decide how to handle it.
    """
    result = df.copy()
    result["Rolling Volatility"] = (
        result["Daily Return"].rolling(window=VOLATILITY_WINDOW).std()
    )
    return result


def calculate_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar-based features derived from the Date column.

    Adds Month (1-12), Quarter (1-4), and Day of Week (0=Monday,
    6=Sunday) columns.

    Args:
        df: A DataFrame with a `Date` column of datetime dtype.

    Returns:
        A new DataFrame with `Month`, `Quarter`, and `Day of Week`
        columns appended.
    """
    result = df.copy()
    result["Month"] = result["Date"].dt.month
    result["Quarter"] = result["Date"].dt.quarter
    result["Day of Week"] = result["Date"].dt.dayofweek
    return result


def save_features(ticker: str, df: pd.DataFrame, filename: str) -> Path:
    """Persist an engineered feature DataFrame to the features directory.

    Args:
        ticker: The ticker symbol (used only for logging context).
        df: The fully engineered DataFrame ready for downstream use.
        filename: The filename to save under (matches the source
            interim filename so files can be traced back to their
            origin).

    Returns:
        The path the CSV file was written to.
    """
    FEATURES_DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = FEATURES_DATA_DIR / filename
    df.to_csv(filepath, index=False)
    return filepath


def process_stock(filepath: Path) -> Optional[Path]:
    """Run the full feature-engineering flow for one cleaned CSV file.

    Any exception raised during processing is caught and logged as
    an error so that a single malformed file never halts the rest of
    the run.

    Args:
        filepath: Path to a cleaned CSV file in `INTERIM_DATA_DIR`.

    Returns:
        The path the engineered CSV was saved to, or None if the file
        failed to load, validate, or otherwise process.
    """
    ticker = filepath.stem

    try:
        df = load_stock_data(filepath)
    except Exception:
        logger.error("Failed to load %s", filepath, exc_info=True)
        return None

    if not _validate_input_columns(ticker, df):
        return None

    try:
        df = calculate_returns(df)
        df = calculate_trend_features(df)
        df = calculate_volatility_features(df)
        df = calculate_time_features(df)
    except Exception:
        logger.error("Failed to engineer features for %s", ticker, exc_info=True)
        return None
    df = df.dropna(how="any").reset_index(drop=True)

    saved_path = save_features(ticker, df, filepath.name)
    _log_feature_metadata(ticker, df, saved_path)
    return saved_path


# ----------------------------------------------------------------------------
# Main Function
# ----------------------------------------------------------------------------
def main() -> None:
    """Engineer features for every cleaned CSV file found in `INTERIM_DATA_DIR`.

    Discovers input files by globbing `INTERIM_DATA_DIR` for `*.csv`
    rather than relying on a hardcoded ticker list, so this module
    stays correct even if the interim directory's contents change
    independently of other modules' configuration.
    """
    interim_files = sorted(INTERIM_DATA_DIR.glob("*.csv"))

    if not interim_files:
        logger.warning("No cleaned CSV files found in %s", INTERIM_DATA_DIR)
        return

    logger.info("Starting feature engineering for %d file(s).", len(interim_files))

    succeeded = 0
    failed = 0

    for filepath in interim_files:
        result = process_stock(filepath)
        if result is not None:
            succeeded += 1
        else:
            failed += 1

    logger.info(
        "Feature engineering run complete. Succeeded: %d | Failed: %d | Output dir: %s",
        succeeded,
        failed,
        FEATURES_DATA_DIR,
    )


# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    _configure_logging()
    main()