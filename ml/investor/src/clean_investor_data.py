
"""Clean and standardize the raw investor/financial trends dataset.

This module is the data-cleaning stage of the Investor Preference
pipeline (a separate pipeline from the Stock Risk Prediction pipeline,
sharing the same architecture and coding conventions). Its sole
responsibility is to load the raw investor survey/assessment data from
``ml/investor/data/raw/financial_trends.csv``, clean and
standardize it, and persist the result to
``ml/investor/data/interim/investor_cleaned.csv``.

This module MUST NOT:
    * Perform feature engineering or exploratory data analysis.
    * Impute or fabricate missing values (only reports them).
    * Train or evaluate any model.

Typical usage:
    python -m src.clean_data
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------
import logging
import re
from pathlib import Path
from typing import Final, Optional

import pandas as pd

# ----------------------------------------------------------------------------
# Configuration / Constants
# ----------------------------------------------------------------------------
# ml/investor/src/clean_data.py -> parent (src) -> parent (investor)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Directory containing the raw investor dataset.
RAW_DATA_DIR: Final[Path] = BASE_DIR / "data" / "raw"

#: Directory where the cleaned, standardized dataset is written.
INTERIM_DATA_DIR: Final[Path] = BASE_DIR / "data" / "interim"

#: Input raw CSV file.
INPUT_FILEPATH = RAW_DATA_DIR / "finance_trends.csv"

#: Output cleaned CSV file.
OUTPUT_FILEPATH: Final[Path] = INTERIM_DATA_DIR / "investor_cleaned.csv"

#: Columns that must be present (after standardization) for the dataset
#: to be considered usable downstream. NOTE: this project does not yet
#: have access to the actual raw file's schema, so this list is left
#: empty as a safe default -- populate it with the real standardized
#: column names (lowercase, underscore-separated) once the raw file's
#: columns are known, e.g. ["age", "income", "credit_score"].
REQUIRED_COLUMNS: Final[list] = [
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
    "source"
]

#: Regex pattern matching any character that is not alphanumeric,
#: whitespace, or an underscore. Used to strip special characters
#: from column names during standardization.
SPECIAL_CHARACTERS_PATTERN: Final[re.Pattern] = re.compile(r"[^\w\s]")

#: Regex pattern matching one or more consecutive whitespace characters.
#: Used to collapse whitespace before converting it to underscores.
WHITESPACE_PATTERN: Final[re.Pattern] = re.compile(r"\s+")

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
def _standardize_column_name(name: str) -> str:
    """Convert a single column name into standardized snake_case form.

    Strips leading/trailing whitespace, removes special characters
    (anything that is not alphanumeric, whitespace, or an underscore),
    collapses internal whitespace, converts to lowercase, and replaces
    spaces with underscores.

    Args:
        name: The original column name.

    Returns:
        The standardized column name, e.g. ``"Credit Score (FICO)"``
        becomes ``"credit_score_fico"``.
    """
    cleaned = name.strip()
    cleaned = SPECIAL_CHARACTERS_PATTERN.sub("", cleaned)
    cleaned = WHITESPACE_PATTERN.sub(" ", cleaned).strip()
    cleaned = cleaned.lower().replace(" ", "_")
    return cleaned


def validate_file_exists(filepath: Path) -> bool:
    """Verify that a required input file exists on disk.

    Args:
        filepath: Path to the expected input file.

    Returns:
        True if the file exists, False otherwise.
    """
    if not filepath.exists():
        logger.error("Input file not found: %s", filepath)
        return False
    return True


# ----------------------------------------------------------------------------
# Core Functions
# ----------------------------------------------------------------------------
def load_data(filepath: Path) -> Optional[pd.DataFrame]:
    """Load the raw investor dataset from a CSV file.

    Args:
        filepath: Path to the raw CSV file.

    Returns:
        The loaded DataFrame, or None if the file could not be read.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception:
        logger.error("Failed to load dataset: %s", filepath, exc_info=True)
        return None

    logger.info("Loaded raw dataset from %s | Shape: %s", filepath, df.shape)
    return df


def validate_dataframe(df: pd.DataFrame) -> bool:
    """Verify that a loaded DataFrame is non-empty and usable.

    Args:
        df: The DataFrame to validate.

    Returns:
        True if the DataFrame contains at least one row and one
        column, False otherwise.
    """
    if df is None or df.empty:
        logger.error("Dataframe is empty; nothing to clean.")
        return False

    if df.shape[1] == 0:
        logger.error("Dataframe has no columns.")
        return False

    return True


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove fully duplicate rows from the dataset.

    Args:
        df: The dataset to deduplicate.

    Returns:
        A new DataFrame with duplicate rows removed and the index
        reset.
    """
    rows_before = len(df)
    deduplicated = df.drop_duplicates().reset_index(drop=True)
    duplicates_removed = rows_before - len(deduplicated)

    if duplicates_removed > 0:
        logger.info("Removed %d duplicate row(s).", duplicates_removed)
    else:
        logger.info("No duplicate rows found.")

    return deduplicated


def clean_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing whitespace from every string (object) column.

    Only touches columns with an `object` dtype (typical for string
    data loaded from CSV); numeric and datetime columns are left
    untouched. Does not alter the values themselves beyond removing
    surrounding whitespace.

    Args:
        df: The dataset to clean.

    Returns:
        A new DataFrame with whitespace stripped from all string
        columns.
    """
    result = df.copy()
    string_columns = result.select_dtypes(include=["object", "string"]).columns

    for column in string_columns:
        result[column] = result[column].str.strip()

    logger.info("Stripped whitespace from %d string column(s): %s", len(string_columns), list(string_columns))
    return result


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize all column names to lowercase snake_case.

    Applies `_standardize_column_name` to every column: lowercases,
    replaces spaces with underscores, and removes special characters.

    Args:
        df: The dataset whose columns should be standardized.

    Returns:
        A new DataFrame with standardized column names.
    """
    result = df.copy()
    rename_map = {col: _standardize_column_name(col) for col in result.columns}
    result = result.rename(columns=rename_map)

    logger.info("Standardized column names: %s", rename_map)
    return result


def validate_required_columns(df: pd.DataFrame) -> bool:
    """Verify that all columns in `REQUIRED_COLUMNS` are present.

    If `REQUIRED_COLUMNS` is empty, this check trivially passes -- it
    is a safe default until the raw dataset's actual schema is known
    and this constant is populated.

    Args:
        df: The dataset (with standardized column names) to validate.

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


def check_missing_values(df: pd.DataFrame) -> pd.Series:
    """Report the count of missing values per column.

    This function only reports missing values; it does not drop,
    impute, or otherwise modify them. Handling missing values is a
    decision left to a later stage of the pipeline.

    Args:
        df: The dataset to inspect.

    Returns:
        A Series indexed by column name with the count of missing
        values in each column (columns with zero missing values are
        included with a value of 0).
    """
    missing_counts = df.isna().sum()
    total_missing = int(missing_counts.sum())

    if total_missing > 0:
        offending_columns = missing_counts[missing_counts > 0].to_dict()
        logger.warning("Missing values found: %s", offending_columns)
    else:
        logger.info("No missing values found in any column.")

    return missing_counts


def summarize_dataset(df: pd.DataFrame, stage: str) -> None:
    """Log summary statistics for the dataset at a given pipeline stage.

    Args:
        df: The dataset to summarize.
        stage: A short label describing when this summary is taken,
            e.g. ``"before cleaning"`` or ``"after cleaning"``.
    """
    memory_usage_mb = df.memory_usage(deep=True).sum() / (1024 ** 2)

    logger.info("----- Dataset Summary (%s) -----", stage)
    logger.info("Shape: %s", df.shape)
    logger.info("Columns: %s", df.columns.tolist())
    logger.info("Dtypes:\n%s", df.dtypes.to_string())
    logger.info("Total missing values: %d", int(df.isna().sum().sum()))
    logger.info("Memory usage: %.4f MB", memory_usage_mb)
    logger.info("---------------------------------")


def save_dataset(df: pd.DataFrame, filepath: Path) -> Optional[Path]:
    """Persist the cleaned dataset to the interim data directory.

    Args:
        df: The fully cleaned dataset.
        filepath: The full path (including filename) to save to.

    Returns:
        The path the CSV file was written to, or None if saving
        failed.
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(filepath, index=False)
    except Exception:
        logger.error("Failed to save cleaned dataset to %s", filepath, exc_info=True)
        return None

    return filepath


# ----------------------------------------------------------------------------
# Main Function
# ----------------------------------------------------------------------------
def main() -> None:
    """Run the full investor data cleaning pipeline end to end.

    Orchestrates: validate input file exists -> load -> validate
    non-empty -> summarize (before) -> remove duplicates -> strip
    string whitespace -> standardize column names -> validate required
    columns -> check missing values -> summarize (after) -> save ->
    print final summary. Aborts early if the input file is missing,
    the dataset is empty, or required columns are missing after
    standardization.
    """
    logger.info("Starting investor data cleaning pipeline.")

    if not validate_file_exists(INPUT_FILEPATH):
        logger.error("Aborting: required input file is missing.")
        return

    raw_df = load_data(INPUT_FILEPATH)

    if raw_df is None or not validate_dataframe(raw_df):
        logger.error("Aborting: dataset could not be loaded or is empty.")
        return

    summarize_dataset(raw_df, stage="before cleaning")

    deduplicated_df = remove_duplicates(raw_df)
    cleaned_strings_df = clean_strings(deduplicated_df)
    standardized_df = standardize_columns(cleaned_strings_df)

    if not validate_required_columns(standardized_df):
        logger.error("Aborting: required columns missing after standardization.")
        return

    check_missing_values(standardized_df)
    summarize_dataset(standardized_df, stage="after cleaning")

    saved_path = save_dataset(standardized_df, OUTPUT_FILEPATH)

    if saved_path is None:
        logger.error("Aborting: failed to save cleaned dataset.")
        return

    print("=" * 60)
    print("Investor Data Cleaning -- Final Summary")
    print("=" * 60)
    print(f"Rows before cleaning : {len(raw_df)}")
    print(f"Rows after cleaning  : {len(standardized_df)}")
    print(f"Columns              : {standardized_df.columns.tolist()}")
    print(f"Saved to             : {saved_path}")
    print("=" * 60)

    logger.info("Investor data cleaning pipeline complete. Saved: %s", saved_path)


# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    setup_logger()
    main()