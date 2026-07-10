"""Clean and standardize raw stock data downloaded by ``download_data.py``.

This module is the data-cleaning stage of the Explainable AI-Based
Portfolio Recommendation System pipeline. Its sole responsibility is
to transform the raw CSV files in ``ml/data/raw/`` into a
standardized, analysis-ready format in ``ml/data/interim/`` --
without altering the underlying stock values.

This module MUST NOT:
    * Perform exploratory data analysis or plotting.
    * Compute technical indicators or engineered features.
    * Train, evaluate, or explain (SHAP/LIME) any model.

Those responsibilities belong to later stages of the pipeline.

Typical usage:
    python -m src.clean_data
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------
import logging
from pathlib import Path
from typing import Final, Optional

import pandas as pd

# ----------------------------------------------------------------------------
# Configuration / Constants
# ----------------------------------------------------------------------------
# ml/src/clean_data.py -> parent (src) -> parent (ml)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Directory containing raw, unmodified CSV files produced by download_data.py.
RAW_DATA_DIR: Final[Path] = BASE_DIR / "data" / "raw"

#: Directory where cleaned, standardized CSV files are written.
INTERIM_DATA_DIR: Final[Path] = BASE_DIR / "data" / "interim"

#: Row indices (0-indexed, after the header row) to skip when reading raw
#: files. yfinance writes a "Ticker" row and a "Date" label row directly
#: beneath the header before the actual data begins.
RAW_METADATA_ROWS_TO_SKIP: Final[list] = [1, 2]

#: The column name yfinance leaves for the date index; renamed to "Date".
RAW_DATE_COLUMN_NAME: Final[str] = "Price"

#: Canonical column order for all cleaned interim files.
CANONICAL_COLUMN_ORDER: Final[list] = [
    "Date",
    "Open",
    "High",
    "Low",
    "Close",
    "Adj Close",
    "Volume",
]

#: Columns that must be present and non-null for a row to be considered usable.
REQUIRED_COLUMNS: Final[tuple] = tuple(CANONICAL_COLUMN_ORDER)

#: Columns that must contain valid data for a row to survive cleaning.
ESSENTIAL_VALUE_COLUMNS: Final[list] = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]

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
def _log_cleaning_metadata(
    ticker: str,
    rows_before: int,
    rows_after: int,
    duplicates_removed: int,
    missing_rows_dropped: int,
    saved_path: Path,
) -> None:
    """Log summary metadata for a successfully cleaned stock file.

    Args:
        ticker: The ticker symbol (derived from the filename).
        rows_before: Row count immediately after loading the raw file.
        rows_after: Row count in the final cleaned DataFrame.
        duplicates_removed: Number of duplicate-date rows dropped.
        missing_rows_dropped: Number of rows dropped due to missing values.
        saved_path: The path the cleaned DataFrame was written to.
    """
    logger.info(
        "Cleaned %s | Rows: %d -> %d | Duplicates removed: %d | "
        "Missing-value rows dropped: %d | Saved: %s",
        ticker,
        rows_before,
        rows_after,
        duplicates_removed,
        missing_rows_dropped,
        saved_path,
    )


# ----------------------------------------------------------------------------
# Core Functions
# ----------------------------------------------------------------------------
def load_stock_data(filepath: Path) -> pd.DataFrame:
    """Load a single raw stock CSV file produced by download_data.py.

    Skips the "Ticker" and "Date" metadata rows that yfinance writes
    beneath the header, so the returned DataFrame contains only the
    header row and actual OHLCV data rows.

    Args:
        filepath: Path to a raw CSV file in `RAW_DATA_DIR`.

    Returns:
        The raw DataFrame exactly as read from disk, with original
        (non-standardized) column names.
    """
    logger.debug("Loading raw file: %s", filepath)
    return pd.read_csv(filepath, skiprows=RAW_METADATA_ROWS_TO_SKIP)


def standardize_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Rename and reorder columns into the canonical schema.

    Renames the leftover index column (`RAW_DATE_COLUMN_NAME`, e.g.
    "Price") to "Date" and reorders all columns to
    `CANONICAL_COLUMN_ORDER`. Does not modify any values.

    Args:
        df: A DataFrame as returned by `load_stock_data`.

    Returns:
        A new DataFrame with standardized column names and order.

    Raises:
        KeyError: If a column referenced in `CANONICAL_COLUMN_ORDER`
            does not exist after renaming (surfaced to the caller so
            `validate_columns` -- not this function -- is responsible
            for deciding whether to skip the file).
    """
    renamed = df.rename(columns={RAW_DATE_COLUMN_NAME: "Date"})

    # Only reorder columns that are actually present; missing columns
    # are a validation concern, not something this function silently
    # papers over.
    available_columns = [col for col in CANONICAL_COLUMN_ORDER if col in renamed.columns]
    return renamed[available_columns].copy()


def validate_columns(ticker: str, df: pd.DataFrame) -> bool:
    """Verify that a standardized DataFrame has all required columns.

    Performs validation only -- no cleaning or modification.

    Args:
        ticker: The ticker symbol (used only for logging context).
        df: A DataFrame as returned by `standardize_headers`.

    Returns:
        True if every column in `REQUIRED_COLUMNS` is present, False
        otherwise.
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


def convert_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """Convert the Date column to datetime and OHLCV columns to numeric.

    Values that cannot be parsed are coerced to NaT/NaN rather than
    raising, so a single malformed cell does not abort processing for
    the entire file. Downstream, `handle_missing_values` is
    responsible for deciding what happens to the resulting NaNs.

    Args:
        df: A DataFrame as returned by `standardize_headers`.

    Returns:
        A new DataFrame with converted dtypes.
    """
    converted = df.copy()
    converted["Date"] = pd.to_datetime(converted["Date"], errors="coerce")

    for column in ESSENTIAL_VALUE_COLUMNS:
        converted[column] = pd.to_numeric(converted[column], errors="coerce")

    return converted


def handle_missing_values(ticker: str, df: pd.DataFrame) -> tuple:
    """Drop rows with missing Date or essential OHLCV values.

    No imputation or interpolation is performed -- rows with
    unusable values are removed rather than estimated, since
    fabricating values is a modeling decision outside this module's
    scope.

    Args:
        ticker: The ticker symbol (used only for logging context).
        df: A DataFrame as returned by `convert_data_types`.

    Returns:
        A tuple of (cleaned_df, rows_dropped) where `cleaned_df` has
        all incomplete rows removed and `rows_dropped` is the count
        of rows that were removed.
    """
    rows_before = len(df)
    subset_columns = ["Date"] + ESSENTIAL_VALUE_COLUMNS
    cleaned = df.dropna(subset=subset_columns).copy()
    rows_dropped = rows_before - len(cleaned)

    if rows_dropped > 0:
        logger.warning("%s: dropped %d row(s) with missing values.", ticker, rows_dropped)

    return cleaned, rows_dropped


def remove_duplicates(ticker: str, df: pd.DataFrame) -> tuple:
    """Remove rows with duplicate Date values, keeping the first occurrence.

    Args:
        ticker: The ticker symbol (used only for logging context).
        df: A DataFrame as returned by `handle_missing_values`.

    Returns:
        A tuple of (deduplicated_df, duplicates_removed).
    """
    rows_before = len(df)
    deduplicated = df.drop_duplicates(subset=["Date"], keep="first").copy()
    duplicates_removed = rows_before - len(deduplicated)

    if duplicates_removed > 0:
        logger.warning("%s: removed %d duplicate row(s).", ticker, duplicates_removed)

    return deduplicated, duplicates_removed


def sort_data(df: pd.DataFrame) -> pd.DataFrame:
    """Sort rows chronologically by Date and reset the index.

    Args:
        df: A DataFrame as returned by `remove_duplicates`.

    Returns:
        A new DataFrame sorted ascending by Date with a fresh,
        contiguous integer index.
    """
    return df.sort_values("Date").reset_index(drop=True)


def save_clean_data(ticker: str, df: pd.DataFrame, filename: str) -> Path:
    """Persist a cleaned DataFrame to the interim data directory.

    Args:
        ticker: The ticker symbol (used only for logging context).
        df: A fully cleaned DataFrame ready for downstream use.
        filename: The filename to save under (matches the source
            raw filename so files can be traced back to their origin).

    Returns:
        The path the CSV file was written to.
    """
    INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = INTERIM_DATA_DIR / filename
    df.to_csv(filepath, index=False)
    return filepath


def process_stock(filepath: Path) -> Optional[Path]:
    """Run the full clean-and-standardize flow for one raw CSV file.

    Any exception raised during processing is caught and logged as
    an error so that a single malformed file never halts the rest of
    the run.

    Args:
        filepath: Path to a raw CSV file in `RAW_DATA_DIR`.

    Returns:
        The path the cleaned CSV was saved to, or None if the file
        failed to load, validate, or otherwise process.
    """
    ticker = filepath.stem

    try:
        raw_df = load_stock_data(filepath)
        standardized_df = standardize_headers(raw_df)
    except Exception:
        logger.error("Failed to load or standardize %s", filepath, exc_info=True)
        return None

    if not validate_columns(ticker, standardized_df):
        return None

    rows_before = len(standardized_df)

    typed_df = convert_data_types(standardized_df)
    no_missing_df, missing_rows_dropped = handle_missing_values(ticker, typed_df)
    deduplicated_df, duplicates_removed = remove_duplicates(ticker, no_missing_df)
    sorted_df = sort_data(deduplicated_df)

    if sorted_df.empty:
        logger.warning("%s: no usable rows remained after cleaning; skipping save.", ticker)
        return None

    saved_path = save_clean_data(ticker, sorted_df, filepath.name)

    _log_cleaning_metadata(
        ticker=ticker,
        rows_before=rows_before,
        rows_after=len(sorted_df),
        duplicates_removed=duplicates_removed,
        missing_rows_dropped=missing_rows_dropped,
        saved_path=saved_path,
    )
    return saved_path


# ----------------------------------------------------------------------------
# Main Function
# ----------------------------------------------------------------------------
def main() -> None:
    """Clean every raw CSV file found in `RAW_DATA_DIR`.

    Discovers input files by globbing `RAW_DATA_DIR` for `*.csv`
    rather than relying on a hardcoded ticker list, so this module
    stays correct even if the raw directory's contents change
    independently of download_data.py's configuration.
    """
    raw_files = sorted(RAW_DATA_DIR.glob("*.csv"))

    if not raw_files:
        logger.warning("No raw CSV files found in %s", RAW_DATA_DIR)
        return

    logger.info("Starting cleaning for %d raw file(s).", len(raw_files))

    succeeded = 0
    failed = 0

    for filepath in raw_files:
        result = process_stock(filepath)
        if result is not None:
            succeeded += 1
        else:
            failed += 1

    logger.info(
        "Cleaning run complete. Succeeded: %d | Failed: %d | Output dir: %s",
        succeeded,
        failed,
        INTERIM_DATA_DIR,
    )


# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    _configure_logging()
    main()