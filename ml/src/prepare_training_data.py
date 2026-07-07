"""Prepare the combined master dataset used for future ML model training.

This module is the ML data-preparation stage of the Explainable
AI-Based Portfolio Recommendation System pipeline. Its sole
responsibility is to merge the per-stock engineered feature files in
``ml/data/features/`` into a single, validated master dataset and
persist it to ``ml/data/processed/training_dataset.csv``.

This module MUST NOT:
    * Perform feature engineering or exploratory data analysis.
    * Perform scaling, encoding, or a train/test split.
    * Train, evaluate, or explain (SHAP/LIME) any model.
    * Implement recommendation logic.

Those responsibilities belong to later stages of the pipeline.

Typical usage:
    python -m src.prepare_training_data
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
# ml/src/prepare_training_data.py -> parent (src) -> parent (ml)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Directory containing per-stock engineered feature CSVs.
FEATURES_DATA_DIR: Final[Path] = BASE_DIR / "data" / "features"

#: Directory where the combined training dataset is written.
PROCESSED_DATA_DIR: Final[Path] = BASE_DIR / "data" / "processed"

#: Filename for the final combined training dataset.
OUTPUT_FILENAME: Final[str] = "training_dataset.csv"

#: Columns to drop from the combined dataset, if present. Empty for now;
#: kept as a named hook so future column removals don't require
#: restructuring the pipeline.
COLUMNS_TO_DROP: Final[list] = []

#: Columns that identify a row rather than measure something numeric.
NON_NUMERIC_COLUMNS: Final[tuple] = ("Date", "Stock")

#: Columns that together uniquely identify a row in the combined dataset.
ROW_IDENTIFIER_COLUMNS: Final[list] = ["Stock", "Date"]

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
def extract_ticker_from_filename(filepath: Path) -> str:
    """Derive a ticker/stock identifier from a feature file's name.

    Args:
        filepath: Path to a feature CSV, e.g. ``RELIANCE_NS.csv``.

    Returns:
        The filename stem, e.g. ``"RELIANCE_NS"``.
    """
    return filepath.stem


# ----------------------------------------------------------------------------
# Core Functions
# ----------------------------------------------------------------------------
def discover_feature_files() -> list:
    """Find all engineered feature CSV files to merge.

    Returns:
        A sorted list of paths to CSV files in `FEATURES_DATA_DIR`.
    """
    return sorted(FEATURES_DATA_DIR.glob("*.csv"))


def load_stock_features(filepath: Path) -> pd.DataFrame:
    """Load a single engineered feature CSV and tag it with its Stock identifier.

    Args:
        filepath: Path to a feature CSV file in `FEATURES_DATA_DIR`.

    Returns:
        The loaded DataFrame with the Date column parsed as datetime
        and a `Stock` column inserted as the first column.
    """
    ticker = extract_ticker_from_filename(filepath)
    logger.debug("Loading feature file: %s", filepath)

    df = pd.read_csv(filepath, parse_dates=["Date"])
    df.insert(0, "Stock", ticker)
    return df


def load_all_stock_features() -> list:
    """Load every discovered feature file, skipping any that fail.

    A single malformed or unreadable file is logged as an error and
    excluded from the result rather than aborting the entire run.

    Returns:
        A list of per-stock DataFrames, each already tagged with a
        `Stock` column.
    """
    filepaths = discover_feature_files()

    if not filepaths:
        logger.warning("No feature files found in %s", FEATURES_DATA_DIR)
        return []

    dataframes = []

    for filepath in filepaths:
        try:
            df = load_stock_features(filepath)
        except Exception:
            logger.error("Failed to load %s", filepath, exc_info=True)
            continue
        dataframes.append(df)

    return dataframes


def merge_stock_data(dataframes: list) -> pd.DataFrame:
    """Concatenate per-stock DataFrames into a single combined dataset.

    Args:
        dataframes: A list of per-stock DataFrames sharing the same
            column schema.

    Returns:
        A single DataFrame containing all rows from all inputs.

    Raises:
        ValueError: If `dataframes` is empty, since there is nothing
            to merge.
    """
    if not dataframes:
        raise ValueError("No dataframes provided to merge.")

    return pd.concat(dataframes, ignore_index=True)


def remove_unnecessary_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop any columns listed in `COLUMNS_TO_DROP`, if present.

    Args:
        df: The combined dataset.

    Returns:
        A new DataFrame with configured columns removed. If
        `COLUMNS_TO_DROP` is empty, an unmodified copy is returned.
    """
    columns_present = [col for col in COLUMNS_TO_DROP if col in df.columns]

    if columns_present:
        logger.info("Dropping unnecessary columns: %s", columns_present)

    return df.drop(columns=columns_present)


def sort_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Sort the combined dataset by Stock, then Date, and reset the index.

    Args:
        df: The combined dataset.

    Returns:
        A new DataFrame sorted ascending by Stock and Date with a
        fresh, contiguous integer index.
    """
    return df.sort_values(ROW_IDENTIFIER_COLUMNS).reset_index(drop=True)


def drop_incomplete_rows(df: pd.DataFrame) -> tuple:
    """Remove rows containing any missing values.

    Engineered features such as SMA_50 or Rolling Volatility are
    undefined for the first N rows of each stock (the rolling-window
    warm-up period). This function removes those incomplete rows so
    the final dataset has no missing values, without inventing or
    modifying any value -- it only removes records that are not yet
    complete.

    Args:
        df: The sorted, combined dataset.

    Returns:
        A tuple of (cleaned_df, rows_dropped) where `cleaned_df` has
        all rows containing at least one missing value removed, and
        `rows_dropped` is the count of rows removed.
    """
    rows_before = len(df)

    FEATURE_COLUMNS_WITH_WARMUP = [
    "SMA_20",
    "SMA_50",
    "Rolling Volatility"
]

    cleaned = df.dropna(subset=FEATURE_COLUMNS_WITH_WARMUP).reset_index(drop=True)
    rows_dropped = rows_before - len(cleaned)

    if rows_dropped > 0:
        logger.info(
            "Dropped %d row(s) containing missing values (rolling-window warm-up period).",
            rows_dropped,
        )

    return cleaned, rows_dropped


def validate_missing_values(df: pd.DataFrame) -> bool:
    """Verify the dataset contains no missing values.

    Args:
        df: The dataset to validate.

    Returns:
        True if there are zero missing values across all columns,
        False otherwise.
    """
    missing_counts = df.isna().sum()
    total_missing = int(missing_counts.sum())

    if total_missing > 0:
        offending_columns = missing_counts[missing_counts > 0].to_dict()
        logger.error("Missing values found: %s", offending_columns)
        return False

    return True


def validate_numeric_columns(df: pd.DataFrame) -> bool:
    """Verify that all non-identifier columns are numeric.

    Args:
        df: The dataset to validate.

    Returns:
        True if every column except `NON_NUMERIC_COLUMNS` has a
        numeric dtype, False otherwise.
    """
    numeric_candidate_columns = [col for col in df.columns if col not in NON_NUMERIC_COLUMNS]
    non_numeric = [
        col for col in numeric_candidate_columns if not pd.api.types.is_numeric_dtype(df[col])
    ]

    if non_numeric:
        logger.error("Non-numeric feature columns found: %s", non_numeric)
        return False

    return True


def validate_duplicate_rows(df: pd.DataFrame) -> bool:
    """Verify there are no duplicate (Stock, Date) rows.

    (Stock, Date) is treated as the dataset's logical row identifier;
    a duplicate combination would mean the same stock/day appears more
    than once.

    Args:
        df: The dataset to validate.

    Returns:
        True if no duplicate (Stock, Date) pairs exist, False
        otherwise.
    """
    duplicate_count = int(df.duplicated(subset=ROW_IDENTIFIER_COLUMNS).sum())

    if duplicate_count > 0:
        logger.error("Found %d duplicate (Stock, Date) row(s).", duplicate_count)
        return False

    return True


def validate_dates(df: pd.DataFrame) -> bool:
    """Verify the Date column is a valid datetime column with no invalid entries.

    Args:
        df: The dataset to validate.

    Returns:
        True if `Date` has a datetime dtype and contains no
        unparseable (NaT) values, False otherwise.
    """
    if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        logger.error("Date column is not a valid datetime dtype.")
        return False

    invalid_dates = int(df["Date"].isna().sum())

    if invalid_dates > 0:
        logger.error("Found %d invalid (unparseable) date value(s).", invalid_dates)
        return False

    return True


def validate_dataset(df: pd.DataFrame) -> bool:
    """Run all validation checks required before saving the training dataset.

    Args:
        df: The fully prepared dataset, immediately before saving.

    Returns:
        True only if every individual validation check passes, False
        if any check fails.
    """
    checks = {
        "no missing values": validate_missing_values(df),
        "numeric feature columns": validate_numeric_columns(df),
        "no duplicate (Stock, Date) rows": validate_duplicate_rows(df),
        "valid dates": validate_dates(df),
    }

    for check_name, passed in checks.items():
        logger.info("Validation check '%s': %s", check_name, "PASSED" if passed else "FAILED")

    return all(checks.values())


def summarize_dataset(df: pd.DataFrame) -> None:
    """Log a detailed summary of the final combined training dataset.

    Reports the number of stocks, row count per stock, overall
    dataset shape, feature names, and memory usage.

    Args:
        df: The final, validated dataset.
    """
    stock_counts = df["Stock"].value_counts().sort_index()
    memory_usage_mb = df.memory_usage(deep=True).sum() / (1024 ** 2)

    logger.info("===== Training Dataset Summary =====")
    logger.info("Number of stocks: %d", df["Stock"].nunique())
    logger.info("Rows per stock:")
    for ticker, count in stock_counts.items():
        logger.info("  %s: %d rows", ticker, count)
    logger.info("Final dataset shape: %s", df.shape)
    logger.info("Feature names: %s", df.columns.tolist())
    logger.info("Memory usage: %.2f MB", memory_usage_mb)
    logger.info("=====================================")


def save_training_dataset(df: pd.DataFrame) -> Path:
    """Persist the final combined dataset to the processed data directory.

    Args:
        df: The fully prepared and validated dataset.

    Returns:
        The path the CSV file was written to.
    """
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = PROCESSED_DATA_DIR / OUTPUT_FILENAME
    df.to_csv(filepath, index=False)
    return filepath


# ----------------------------------------------------------------------------
# Main Function
# ----------------------------------------------------------------------------
def main() -> None:
    """Build, validate, and save the combined ML training dataset.

    Orchestrates: load per-stock feature files -> merge -> drop
    unnecessary columns -> sort -> drop incomplete rows -> validate ->
    summarize -> save. If validation fails, the dataset is not saved.
    """
    logger.info("Starting ML training data preparation.")

    dataframes = load_all_stock_features()
    logger.info("Loaded %d feature files.", len(dataframes))

    if not dataframes:
        logger.error("No feature data available to merge. Aborting.")
        return

    try:
        combined_df = merge_stock_data(dataframes)
    except ValueError:
        logger.error("Failed to merge stock data.", exc_info=True)
        return

    combined_df = remove_unnecessary_columns(combined_df)
    combined_df = sort_dataset(combined_df)
    combined_df, rows_dropped = drop_incomplete_rows(combined_df)

    if combined_df.empty:
        logger.error("Dataset is empty after removing incomplete rows. Aborting.")
        return

    if not validate_dataset(combined_df):
        logger.error("Validation failed. Training dataset was NOT saved.")
        return

    summarize_dataset(combined_df)
    saved_path = save_training_dataset(combined_df)

    logger.info(
        "Training data preparation complete. Rows dropped (incomplete): %d | Saved: %s",
        rows_dropped,
        saved_path,
    )


# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    _configure_logging()
    main()