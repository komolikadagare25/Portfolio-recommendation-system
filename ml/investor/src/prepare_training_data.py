
"""Prepare the final investor training dataset for risk labeling.

This module is the final data-preparation stage of the Investor
Profiling pipeline (a separate pipeline from the Stock Risk Prediction
pipeline, sharing the same architecture and coding conventions).
Unlike the Stock pipeline's `prepare_training_data.py`, this module
does not merge multiple files -- the Investor pipeline already has a
single engineered dataset. Its sole responsibility is to validate,
lightly optimize, and reorder that dataset, then persist it as the
final training dataset consumed by `generate_risk_labels.py`.

This module MUST NOT:
    * Perform scaling, normalization, or encoding.
    * Perform a train/test split or feature selection.
    * Fit or use LabelEncoder, OneHotEncoder, or StandardScaler.
    * Train any model (e.g. RandomForest).
    * Generate labels or perform prediction.

Those responsibilities belong to later modules in the pipeline.

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
# Configuration Constants
# ----------------------------------------------------------------------------
# ml/investor/src/prepare_training_data.py -> parent (src) -> parent (investor)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Directory containing the engineered features dataset.
PROCESSED_DATA_DIR: Final[Path] = BASE_DIR / "data" / "processed"

#: Input engineered features CSV, produced by feature_engineering.py.
INPUT_FILEPATH: Final[Path] = PROCESSED_DATA_DIR / "investor_features.csv"

#: Output final training dataset CSV.
OUTPUT_FILEPATH: Final[Path] = PROCESSED_DATA_DIR / "investor_training_dataset.csv"

#: Columns that must be present for this module to proceed. 
REQUIRED_COLUMNS: Final[list] = [
     # Original features
    "gender",
    "age",
    "investment_avenues",
    "mutual_funds",
    "equity_market",
    "debentures",
    "government_bonds",
    "fixed_deposits",
    "ppf",
    "gold",
    "stock_market",
    "factor",
    "objective",
    "purpose",
    "duration",
    "invest_monitor",
    "expect",
    "avenue",
    "what_are_your_savings_objectives",
    "reason_equity",
    "reason_mutual",
    "reason_bonds",
    "reason_fd",
    "source",

    # Engineered features
    "total_investment_score",
    "preferred_safe_assets",
    "preferred_market_assets",
    "investment_diversification_score",
    "age_group",
]

#: Known engineered feature column names produced by
#: feature_engineering.py. Both "diversification_score" (as actually
#: produced) and "investment_diversification_score" (as named in this
#: module's spec) are accepted, so a naming mismatch between the two
#: modules does not silently misclassify a column. Any of these that
#: are present are treated as engineered features and moved to the end
#: of the column order; everything else is treated as an original
#: feature and kept in its existing relative order.
ENGINEERED_FEATURE_COLUMNS: Final[list] = [
    "total_investment_score",
    "preferred_safe_assets",
    "preferred_market_assets",
    "diversification_score",
    "investment_diversification_score",
    "age_group",
]

#: Maximum ratio of unique values to total rows for an object column to
#: be considered a good candidate for conversion to `category` dtype.
#: Kept conservative so genuinely high-cardinality text columns (e.g.
#: free-text or near-unique identifiers) are left as-is.
CATEGORY_CONVERSION_MAX_UNIQUE_RATIO: Final[float] = 0.5

#: Logging verbosity for this module.
LOG_LEVEL: Final[int] = logging.INFO

# ----------------------------------------------------------------------------
# Logger
# ----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def setup_logger() -> None:
    """Attach a basic stream handler to this module's logger.

    Configures the module-level logger with an INFO-level stream
    handler and a timestamped formatter. Applied only when the module
    is run as a script (see the entry point at the bottom of the
    file), so importing this module does not silently attach handlers
    to a caller's logging configuration.
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
def _present_engineered_columns(df: pd.DataFrame) -> list:
    """Return which known engineered feature columns exist in the dataset.

    Args:
        df: The dataset to check.

    Returns:
        The subset of `ENGINEERED_FEATURE_COLUMNS` that are present in
        `df.columns`, in `ENGINEERED_FEATURE_COLUMNS` order.
    """
    return [col for col in ENGINEERED_FEATURE_COLUMNS if col in df.columns]


def _is_good_category_candidate(series: pd.Series) -> bool:
    """Decide whether an object column is a good candidate for `category` dtype.

    A column qualifies if it has an `object` dtype and its ratio of
    unique (non-null) values to total rows is at or below
    `CATEGORY_CONVERSION_MAX_UNIQUE_RATIO`. This keeps genuinely
    high-cardinality text columns as plain strings.

    Args:
        series: The column to evaluate.

    Returns:
        True if the column should be converted to `category` dtype,
        False otherwise.
    """
    if not pd.api.types.is_string_dtype(series):
        return False

    if len(series) == 0:
        return False

    unique_ratio = series.nunique(dropna=True) / len(series)
    return unique_ratio <= CATEGORY_CONVERSION_MAX_UNIQUE_RATIO


# ----------------------------------------------------------------------------
# Validation Functions
# ----------------------------------------------------------------------------
def validate_input_file() -> bool:
    """Verify that the required input file exists on disk.

    Returns:
        True if `INPUT_FILEPATH` exists, False otherwise.
    """
    if not INPUT_FILEPATH.exists():
        logger.error("Input file not found: %s", INPUT_FILEPATH)
        return False
    return True


def validate_dataset(df: pd.DataFrame) -> bool:
    """Run all validation checks required before preparing the dataset.

    Checks that the dataframe loaded successfully and is non-empty,
    that no duplicate column names or duplicate rows exist, that all
    `REQUIRED_COLUMNS` are present, and that no column is completely
    empty. Missing values are reported but do not fail validation.

    Args:
        df: The loaded engineered features dataset.

    Returns:
        True only if every individual validation check passes, False
        if any check fails.
    """
    checks = {
        "dataframe loaded correctly": df is not None,
        "dataframe not empty": df is not None and not df.empty,
        "no duplicate column names": not df.columns.duplicated().any(),
        "no duplicate rows": not df.duplicated().any(),
        "required columns present": _validate_required_columns(df),
        "no completely empty columns": _validate_no_empty_columns(df),
    }

    for check_name, passed in checks.items():
        logger.info("Validation check '%s': %s", check_name, "PASSED" if passed else "FAILED")

    _report_missing_values(df)

    return all(checks.values())


def _validate_required_columns(df: pd.DataFrame) -> bool:
    """Verify that all columns in `REQUIRED_COLUMNS` are present.

    If `REQUIRED_COLUMNS` is empty, this check trivially passes -- a
    safe default until the real dataset schema is known.

    Args:
        df: The dataset to validate.

    Returns:
        True if every column in `REQUIRED_COLUMNS` is present, False
        otherwise.
    """
    if not REQUIRED_COLUMNS:
        logger.warning(
            "REQUIRED_COLUMNS is empty; skipping required-column validation. "
            "Populate this constant once the dataset's real schema is known."
        )
        return True

    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)

    if missing_columns:
        logger.error("Missing required columns: %s", sorted(missing_columns))
        return False

    return True


def _validate_no_empty_columns(df: pd.DataFrame) -> bool:
    """Verify that no column consists entirely of missing values.

    Args:
        df: The dataset to validate.

    Returns:
        True if every column has at least one non-null value, False
        otherwise.
    """
    empty_columns = [col for col in df.columns if df[col].isna().all()]

    if empty_columns:
        logger.error("Completely empty column(s) found: %s", empty_columns)
        return False

    return True


def _report_missing_values(df: pd.DataFrame) -> pd.Series:
    """Report the count of missing values per column.

    Reporting only -- this function does not drop or impute values.

    Args:
        df: The dataset to inspect.

    Returns:
        A Series indexed by column name with the count of missing
        values in each column.
    """
    missing_counts = df.isna().sum()
    total_missing = int(missing_counts.sum())

    if total_missing > 0:
        offending_columns = missing_counts[missing_counts > 0].to_dict()
        logger.warning("Missing values found: %s", offending_columns)
    else:
        logger.info("No missing values found in any column.")

    return missing_counts


def validate_expected_numeric_columns(before_df: pd.DataFrame, after_df: pd.DataFrame) -> bool:
    """Verify that columns numeric before optimization remain numeric after.

    Guards against `optimize_dataframe` accidentally converting a
    numeric column (e.g. an engineered score) into a non-numeric
    dtype such as `category`.

    Args:
        before_df: The dataset prior to optimization.
        after_df: The dataset after optimization.

    Returns:
        True if every column that was numeric in `before_df` is still
        numeric in `after_df`, False otherwise.
    """
    numeric_before = [col for col in before_df.columns if pd.api.types.is_numeric_dtype(before_df[col])]
    no_longer_numeric = [col for col in numeric_before if not pd.api.types.is_numeric_dtype(after_df[col])]

    if no_longer_numeric:
        logger.error("Column(s) lost numeric dtype during optimization: %s", no_longer_numeric)
        return False

    return True


def validate_output_dataset(original_df: pd.DataFrame, final_df: pd.DataFrame) -> bool:
    """Run final validation checks before saving the prepared dataset.

    Checks that the row count is unchanged, no duplicate rows were
    introduced, at least one known engineered feature is present, and
    all `REQUIRED_COLUMNS` are still present.

    Args:
        original_df: The dataset as originally loaded.
        final_df: The fully prepared dataset, immediately before
            saving.

    Returns:
        True only if every individual check passes, False if any
        check fails.
    """
    engineered_present = _present_engineered_columns(final_df)

    checks = {
        "row count unchanged": len(original_df) == len(final_df),
        "no duplicate rows": not final_df.duplicated().any(),
        "engineered features exist": len(engineered_present) > 0,
        "required columns present": _validate_required_columns(final_df),
    }

    for check_name, passed in checks.items():
        logger.info("Output validation check '%s': %s", check_name, "PASSED" if passed else "FAILED")

    return all(checks.values())


# ----------------------------------------------------------------------------
# Core Functions
# ----------------------------------------------------------------------------
def load_dataset(filepath: Path) -> Optional[pd.DataFrame]:
    """Load the engineered investor features dataset from a CSV file.

    Args:
        filepath: Path to the engineered features CSV file.

    Returns:
        The loaded DataFrame, or None if the file could not be read.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception:
        logger.error("Failed to load dataset: %s", filepath, exc_info=True)
        return None

    logger.info("Loaded engineered features dataset from %s | Shape: %s", filepath, df.shape)
    return df


def identify_feature_types(df: pd.DataFrame) -> dict:
    """Classify columns into original and engineered feature groups.

    Args:
        df: The dataset to inspect.

    Returns:
        A dict with keys `original_columns` and `engineered_columns`,
        each a list of column names, preserving each group's relative
        order as it appears in `df`.
    """
    engineered_columns = _present_engineered_columns(df)
    original_columns = [col for col in df.columns if col not in engineered_columns]

    logger.info("Identified %d original feature column(s): %s", len(original_columns), original_columns)
    logger.info("Identified %d engineered feature column(s): %s", len(engineered_columns), engineered_columns)

    return {"original_columns": original_columns, "engineered_columns": engineered_columns}


def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Lightly optimize dataframe dtypes without changing any values.

    Converts low-cardinality `object` columns to `category` dtype
    (see `_is_good_category_candidate`) for memory efficiency. Numeric
    and existing category/datetime columns are left untouched, and no
    scaling, normalization, or encoding is performed.

    Args:
        df: The validated dataset.

    Returns:
        A new DataFrame with optimized dtypes.
    """
    result = df.copy()
    converted_columns = []
    string_columns = [col for col in result.columns if pd.api.types.is_string_dtype(result[col])]

    for column in string_columns:
        if _is_good_category_candidate(result[column]):
            result[column] = result[column].astype("category")
            converted_columns.append(column)

    if converted_columns:
        logger.info("Converted %d column(s) to category dtype: %s", len(converted_columns), converted_columns)
    else:
        logger.info("No columns were converted to category dtype.")

    return result


def reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Reorder columns so original features come first, engineered features last.

    Original feature columns keep their existing relative order;
    known engineered feature columns (see `ENGINEERED_FEATURE_COLUMNS`)
    are moved to the end, in that constant's order.

    Args:
        df: The dataset to reorder.

    Returns:
        A new DataFrame with columns reordered: original features
        followed by engineered features.
    """
    feature_types = identify_feature_types(df)
    ordered_columns = feature_types["original_columns"] + feature_types["engineered_columns"]

    return df[ordered_columns]


# ----------------------------------------------------------------------------
# Save Functions
# ----------------------------------------------------------------------------
def save_dataset(df: pd.DataFrame, filepath: Path) -> Optional[Path]:
    """Persist the final training dataset to the processed data directory.

    Args:
        df: The fully prepared dataset.
        filepath: The full path (including filename) to save to.

    Returns:
        The path the CSV file was written to, or None if saving
        failed.
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(filepath, index=False)
    except Exception:
        logger.error("Failed to save training dataset to %s", filepath, exc_info=True)
        return None

    return filepath


# ----------------------------------------------------------------------------
# Dataset Summary
# ----------------------------------------------------------------------------
def summarize_dataset(original_df: pd.DataFrame, final_df: pd.DataFrame, saved_path: Path) -> None:
    """Print and log a detailed summary of the training data preparation run.

    Args:
        original_df: The dataset as originally loaded.
        final_df: The final prepared dataset.
        saved_path: The path the final dataset was saved to.
    """
    feature_types = identify_feature_types(final_df)
    original_feature_count = len(feature_types["original_columns"])
    engineered_feature_count = len(feature_types["engineered_columns"])
    memory_usage_mb = final_df.memory_usage(deep=True).sum() / (1024 ** 2)
    total_missing = int(final_df.isna().sum().sum())

    logger.info("===== Investor Training Data Preparation Summary =====")
    logger.info("Input rows: %d", len(original_df))
    logger.info("Output rows: %d", len(final_df))
    logger.info("Column count: %d", final_df.shape[1])
    logger.info("Original feature count: %d", original_feature_count)
    logger.info("Engineered feature count: %d", engineered_feature_count)
    logger.info("Engineered feature names: %s", feature_types["engineered_columns"])
    logger.info("Memory usage: %.4f MB", memory_usage_mb)
    logger.info("Missing values: %d", total_missing)
    logger.info("Output path: %s", saved_path)
    logger.info("========================================================")

    print("=" * 60)
    print("Investor Training Data Preparation -- Final Summary")
    print("=" * 60)
    print(f"Input rows            : {len(original_df)}")
    print(f"Output rows           : {len(final_df)}")
    print(f"Column count          : {final_df.shape[1]}")
    print(f"Original feature count: {original_feature_count}")
    print(f"Engineered feature count: {engineered_feature_count}")
    print(f"Engineered feature names: {feature_types['engineered_columns']}")
    print(f"Memory usage (MB)     : {memory_usage_mb:.4f}")
    print(f"Missing values        : {total_missing}")
    print(f"Saved to              : {saved_path}")
    print("=" * 60)


# ----------------------------------------------------------------------------
# Main Function
# ----------------------------------------------------------------------------
def main() -> None:
    """Run the full investor training data preparation pipeline end to end.

    Orchestrates: validate input file exists -> load -> validate
    dataset -> identify feature types -> optimize dtypes -> validate
    numeric columns preserved -> reorder columns -> validate output ->
    save -> summarize. Aborts early if the input file is missing, the
    dataset fails validation, dtype optimization breaks a numeric
    column, or the final output fails validation.
    """
    logger.info("Starting investor training data preparation pipeline.")

    if not validate_input_file():
        logger.error("Aborting: required input file is missing.")
        return

    df = load_dataset(INPUT_FILEPATH)

    if df is None or not validate_dataset(df):
        logger.error("Aborting: dataset could not be loaded or failed validation.")
        return

    identify_feature_types(df)

    optimized_df = optimize_dataframe(df)

    if not validate_expected_numeric_columns(df, optimized_df):
        logger.error("Aborting: dtype optimization altered numeric columns.")
        return

    final_df = reorder_columns(optimized_df)

    if not validate_output_dataset(df, final_df):
        logger.error("Aborting: final dataset failed output validation.")
        return

    saved_path = save_dataset(final_df, OUTPUT_FILEPATH)

    if saved_path is None:
        logger.error("Aborting: failed to save training dataset.")
        return

    summarize_dataset(df, final_df, saved_path)
    logger.info("Investor training data preparation complete. Saved: %s", saved_path)


# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    setup_logger()
    main()