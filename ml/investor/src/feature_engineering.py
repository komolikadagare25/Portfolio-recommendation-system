"""Engineer investor-preference features from the cleaned investor dataset.

This module is the feature-engineering stage of the Investor Profiling
pipeline (a separate pipeline from the Stock Risk Prediction pipeline,
sharing the same architecture and coding conventions). Its sole
responsibility is to load the cleaned dataset from
``ml/investor/data/interim/investor_cleaned.csv``, derive a small set
of logically meaningful, non-leaky investor features, and persist the
result to ``ml/investor/data/processed/investor_features.csv``.

This module MUST NOT:
    * Train any ML model.
    * Perform a train/test split.
    * Fit a LabelEncoder, OneHotEncoder, or StandardScaler.
    * Save any encoder/scaler object.
    * Generate labels or perform prediction.

Those responsibilities belong to later modules in the pipeline.

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
# Configuration Constants
# ----------------------------------------------------------------------------
# ml/investor/src/feature_engineering.py -> parent (src) -> parent (investor)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Directory containing the cleaned interim dataset.
INTERIM_DATA_DIR: Final[Path] = BASE_DIR / "data" / "interim"

#: Directory where the engineered feature dataset is written.
PROCESSED_DATA_DIR: Final[Path] = BASE_DIR / "data" / "processed"

#: Input cleaned CSV file, produced by clean_data.py.
INPUT_FILEPATH: Final[Path] = INTERIM_DATA_DIR / "investor_cleaned.csv"

#: Output engineered features CSV file.
OUTPUT_FILEPATH: Final[Path] = PROCESSED_DATA_DIR / "investor_features.csv"

#: Columns that must be present for this module to proceed. NOTE: this
#: project does not yet have access to the real cleaned dataset's
#: schema, so this list is left empty as a safe default -- populate it
#: with the actual standardized column names once known.
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
    "source",
]

#: Candidate investment-avenue columns considered for total_investment_score
#: and diversification_score. Only columns that actually exist in the
#: loaded dataset are used; missing ones are logged and skipped rather
#: than assumed.
INVESTMENT_AVENUE_COLUMNS = [
    "mutual_funds",
    "equity_market",
    "government_bonds",
    "fixed_deposits",
    "ppf",
    "gold",
]

#: Candidate columns representing traditionally "safe" investment avenues.
SAFE_ASSET_COLUMNS: Final[list] = [
    "government_bonds",
    "fixed_deposits",
    "ppf",
]

#: Candidate columns representing market-linked investment avenues.
MARKET_ASSET_COLUMNS: Final[list] = [
    "equity_market",
    "stock_market",
]

#: Candidate columns expected to hold Yes/No style values, standardized
#: to consistent "Yes"/"No" text (not encoded to 0/1 -- encoding is
#: explicitly out of scope for this module).
YES_NO_CANDIDATE_VALUES: Final[set] = {"yes", "no", "y", "n", "true", "false"}

#: Column expected to hold the investor's age, used to derive age_group.
AGE_COLUMN: Final[str] = "age"

#: Age bin edges and labels for the age_group feature. Bounds are
#: inclusive of the lower edge; documented as an explicit, stated
#: assumption rather than an arbitrary hidden threshold.
AGE_BIN_EDGES = [0, 25, 50, 150]
AGE_BIN_LABELS = ["Young", "Adult", "Senior"]

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
def _available_columns(df: pd.DataFrame, candidate_columns: list) -> list:
    """Filter a candidate column list down to columns actually present.

    Logs a warning for any candidate columns that are missing, so a
    dependent engineered feature can be computed from a partial set
    without silently pretending nothing was missing.

    Args:
        df: The dataset to check against.
        candidate_columns: Column names that would ideally be used.

    Returns:
        The subset of `candidate_columns` that exist in `df.columns`.
    """
    present = [col for col in candidate_columns if col in df.columns]
    missing = [col for col in candidate_columns if col not in df.columns]

    if missing:
        logger.warning("Candidate columns not found and will be skipped: %s", missing)

    return present


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
    """Run all validation checks required before feature engineering.

    Checks that the dataframe loaded successfully and is non-empty,
    that no duplicate column names exist, that no duplicate rows
    exist, that all `REQUIRED_COLUMNS` are present, and reports (but
    does not act on) missing values.

    Args:
        df: The loaded, cleaned dataset.

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


def validate_expected_numeric_columns(df: pd.DataFrame, numeric_columns: list) -> bool:
    """Verify that a given set of columns holds numeric dtypes.

    Args:
        df: The dataset to validate.
        numeric_columns: Column names expected to be numeric.

    Returns:
        True if every present column in `numeric_columns` has a
        numeric dtype, False otherwise.
    """
    present_columns = [col for col in numeric_columns if col in df.columns]
    non_numeric = [col for col in present_columns if not pd.api.types.is_numeric_dtype(df[col])]

    if non_numeric:
        logger.error("Expected numeric columns are not numeric: %s", non_numeric)
        return False

    return True


def validate_output_dataset(original_df: pd.DataFrame, engineered_df: pd.DataFrame) -> bool:
    """Verify the engineered dataset is consistent with the input dataset.

    Checks that no rows were added or dropped during feature
    engineering and that the engineered dataset is non-empty.

    Args:
        original_df: The dataset before feature engineering.
        engineered_df: The dataset after feature engineering.

    Returns:
        True if the row count is unchanged and the result is
        non-empty, False otherwise.
    """
    checks = {
        "row count unchanged": len(original_df) == len(engineered_df),
        "engineered dataset not empty": not engineered_df.empty,
    }

    for check_name, passed in checks.items():
        logger.info("Output validation check '%s': %s", check_name, "PASSED" if passed else "FAILED")

    return all(checks.values())


# ----------------------------------------------------------------------------
# Core Feature Engineering Functions
# ----------------------------------------------------------------------------
def load_dataset(filepath: Path) -> Optional[pd.DataFrame]:
    """Load the cleaned investor dataset from a CSV file.

    Args:
        filepath: Path to the cleaned CSV file.

    Returns:
        The loaded DataFrame, or None if the file could not be read.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception:
        logger.error("Failed to load dataset: %s", filepath, exc_info=True)
        return None

    logger.info("Loaded cleaned dataset from %s | Shape: %s", filepath, df.shape)
    return df


def identify_feature_types(df: pd.DataFrame) -> dict:
    """Classify columns into numeric and categorical groups.

    Args:
        df: The dataset to inspect.

    Returns:
        A dict with keys `numeric_columns` and `categorical_columns`,
        each a list of column names.
    """
    numeric_columns = df.select_dtypes(include=np.number).columns.tolist()
    categorical_columns = df.select_dtypes(include=["object", "string"]).columns.tolist()

    logger.info("Identified %d numeric column(s): %s", len(numeric_columns), numeric_columns)
    logger.info("Identified %d categorical column(s): %s", len(categorical_columns), categorical_columns)

    return {"numeric_columns": numeric_columns, "categorical_columns": categorical_columns}


def standardize_categorical_values(df: pd.DataFrame) -> pd.DataFrame:
    """Trim whitespace and apply consistent title-case capitalization.

    Applies only to columns with an `object` dtype. This does not
    change the meaning of any value -- only its surface formatting
    (e.g. ``" single "`` and ``"SINGLE"`` both become ``"Single"``).

    Args:
        df: The dataset to standardize.

    Returns:
        A new DataFrame with standardized categorical text values.
    """
    result = df.copy()
    categorical_columns = result.select_dtypes(include=["object", "string"]).columns

    for column in categorical_columns:
        result[column] = result[column].str.strip().str.title()

    logger.info("Standardized capitalization for %d categorical column(s).", len(categorical_columns))
    return result


def standardize_yes_no_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize binary Yes/No style columns to consistent "Yes"/"No" text.

    A column is treated as Yes/No style if every one of its non-null
    values (case-insensitively) belongs to `YES_NO_CANDIDATE_VALUES`.
    Values are mapped to the literal strings "Yes"/"No" -- this is
    text standardization, not label encoding (no numeric 0/1 mapping
    is produced here; that is left to the model training pipeline).

    Args:
        df: The dataset to standardize.

    Returns:
        A new DataFrame with detected Yes/No columns standardized.
    """
    result = df.copy()
    yes_values = {"yes", "y", "true"}
    standardized_columns = []

    for column in result.select_dtypes(include=["object", "string"]).columns:
        non_null_values = result[column].dropna().str.lower().unique().tolist()

        if non_null_values and set(non_null_values).issubset(YES_NO_CANDIDATE_VALUES):
            result[column] = result[column].apply(
                lambda value: ("Yes" if str(value).lower() in yes_values else "No") if pd.notna(value) else value
            )
            standardized_columns.append(column)

    if standardized_columns:
        logger.info("Standardized Yes/No columns: %s", standardized_columns)
    else:
        logger.info("No Yes/No style columns detected.")

    return result


def ensure_numeric_dtypes(df: pd.DataFrame, numeric_columns: list) -> pd.DataFrame:
    """Coerce a given set of columns to numeric dtype where present.

    Values that cannot be parsed as numeric are converted to NaN
    rather than raising, so a single malformed cell does not abort
    processing. Missing values introduced this way are reported by
    `_report_missing_values`, not silently dropped.

    Args:
        df: The dataset to process.
        numeric_columns: Column names that should be numeric.

    Returns:
        A new DataFrame with the specified columns coerced to numeric
        dtype (only for columns that are actually present).
    """
    result = df.copy()
    present_columns = _available_columns(result, numeric_columns)

    for column in present_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    return result


def create_total_investment_score(df: pd.DataFrame) -> pd.DataFrame:
    """Add total_investment_score: sum of available investment-avenue columns.

    Uses whichever of `INVESTMENT_AVENUE_COLUMNS` are actually present
    in the dataset. Missing values within those columns are treated as
    contributing 0 to the sum (pandas' default `skipna=True` row-wise
    sum behavior) -- this is a stated assumption, not an imputation of
    the underlying data.

    Args:
        df: The dataset to add the feature to.

    Returns:
        A new DataFrame with a `total_investment_score` column added,
        or the unmodified dataset if no candidate columns are present.
    """
    result = df.copy()
    available = _available_columns(result, INVESTMENT_AVENUE_COLUMNS)

    if not available:
        logger.warning("Skipping total_investment_score: no investment-avenue columns found.")
        return result

    result["total_investment_score"] = result[available].sum(axis=1, skipna=True)
    logger.info("Created total_investment_score from columns: %s", available)
    return result


def create_preferred_safe_assets(df: pd.DataFrame) -> pd.DataFrame:
    """Add preferred_safe_assets: sum of available safe-asset columns.

    Uses whichever of `SAFE_ASSET_COLUMNS` are actually present.

    Args:
        df: The dataset to add the feature to.

    Returns:
        A new DataFrame with a `preferred_safe_assets` column added,
        or the unmodified dataset if no candidate columns are present.
    """
    result = df.copy()
    available = _available_columns(result, SAFE_ASSET_COLUMNS)

    if not available:
        logger.warning("Skipping preferred_safe_assets: no safe-asset columns found.")
        return result

    result["preferred_safe_assets"] = result[available].sum(axis=1, skipna=True)
    logger.info("Created preferred_safe_assets from columns: %s", available)
    return result


def create_preferred_market_assets(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create preferred_market_assets feature.

    Combines the investor's preference for Equity Market and Stock Market.

    The stock_market column contains Yes/No values, so it is converted
    temporarily to 1/0 only for this calculation.
    """

    result = df.copy()

    if "equity_market" not in result.columns:
        logger.warning("Skipping preferred_market_assets: equity_market not found.")
        return result

    equity = result["equity_market"]

    if "stock_market" in result.columns:

        stock_market_numeric = (
            result["stock_market"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({
                "yes": 1,
                "no": 0
            })
            .fillna(0)
        )

    else:
        logger.warning("stock_market column not found.")
        stock_market_numeric = 0

    result["preferred_market_assets"] = equity + stock_market_numeric

    logger.info(
    "Created preferred_market_assets using equity_market + stock_market (Yes=1, No=0)."
)

    return result

def create_diversification_score(df: pd.DataFrame) -> pd.DataFrame:
    """Add diversification_score: count of investment avenues with positive preference.

    Uses whichever of `INVESTMENT_AVENUE_COLUMNS` are actually present.
    A value greater than 0 in a given avenue column counts as one
    "diversified into" that avenue for that row.

    Args:
        df: The dataset to add the feature to.

    Returns:
        A new DataFrame with a `diversification_score` column added,
        or the unmodified dataset if no candidate columns are present.
    """
    result = df.copy()
    available = _available_columns(result, INVESTMENT_AVENUE_COLUMNS)

    if not available:
        logger.warning("Skipping diversification_score: no investment-avenue columns found.")
        return result

    result["investment_diversification_score"] = (result[available] > 0).sum(axis=1)
    logger.info("Created investment_diversification_score from columns: %s", available)
    return result


def create_age_group(df: pd.DataFrame) -> pd.DataFrame:
    """Add age_group: a Young/Adult/Senior category derived from age.

    Bin edges are `AGE_BIN_EDGES` with labels `AGE_BIN_LABELS`
    (default: 0-25 Young, 26-50 Adult, 51+ Senior). This is a stated,
    documented assumption about age boundaries, not a hidden
    arbitrary threshold.

    Args:
        df: The dataset to add the feature to.

    Returns:
        A new DataFrame with an `age_group` column added, or the
        unmodified dataset if `AGE_COLUMN` is not present.
    """
    result = df.copy()

    if AGE_COLUMN not in result.columns:
        logger.warning("Skipping age_group: '%s' column not found.", AGE_COLUMN)
        return result

    result["age_group"] = pd.cut(
        result[AGE_COLUMN],
        bins=AGE_BIN_EDGES,
        labels=AGE_BIN_LABELS,
        right=True,
        include_lowest=True,
    )
    

    logger.info("Created age_group from '%s' using bins %s -> %s", AGE_COLUMN, AGE_BIN_EDGES, AGE_BIN_LABELS)
    return result


def create_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Run all feature engineering steps in sequence.

    Standardizes existing values first, then derives new columns.
    Each derived feature is skipped (with a logged warning) if its
    required source columns are not present, rather than failing the
    entire pipeline.

    Args:
        df: The validated, cleaned dataset.

    Returns:
        A new DataFrame containing the original columns plus any
        successfully engineered features.
    """
    result = standardize_categorical_values(df)
    result = standardize_yes_no_columns(result)

    numeric_candidates = list(
    dict.fromkeys(
        INVESTMENT_AVENUE_COLUMNS
        + SAFE_ASSET_COLUMNS
        + [AGE_COLUMN]
    )
)
    result = ensure_numeric_dtypes(result, numeric_candidates)

    result = create_total_investment_score(result)
    result = create_preferred_safe_assets(result)
    result = create_preferred_market_assets(result)
    result = create_diversification_score(result)
    result = create_age_group(result)

    return result


# ----------------------------------------------------------------------------
# Save Functions
# ----------------------------------------------------------------------------
def save_dataset(df: pd.DataFrame, filepath: Path) -> Optional[Path]:
    """Persist the engineered dataset to the processed data directory.

    Args:
        df: The fully engineered dataset.
        filepath: The full path (including filename) to save to.

    Returns:
        The path the CSV file was written to, or None if saving
        failed.
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(filepath, index=False)
    except Exception:
        logger.error("Failed to save engineered dataset to %s", filepath, exc_info=True)
        return None

    return filepath


# ----------------------------------------------------------------------------
# Dataset Summary
# ----------------------------------------------------------------------------
def summarize_dataset(original_df: pd.DataFrame, engineered_df: pd.DataFrame, saved_path: Path) -> None:
    """Print and log a detailed summary of the feature engineering run.

    Args:
        original_df: The dataset before feature engineering.
        engineered_df: The final engineered dataset.
        saved_path: The path the engineered dataset was saved to.
    """
    original_columns = set(original_df.columns)
    new_columns = [col for col in engineered_df.columns if col not in original_columns]
    memory_usage_mb = engineered_df.memory_usage(deep=True).sum() / (1024 ** 2)
    missing_counts = engineered_df.isna().sum()
    total_missing = int(missing_counts.sum())

    logger.info("===== Feature Engineering Summary =====")
    logger.info("Rows: %d", len(engineered_df))
    logger.info("Columns: %d", engineered_df.shape[1])
    logger.info("Original feature count: %d", original_df.shape[1])
    logger.info("New feature count: %d", len(new_columns))
    logger.info("Engineered feature names: %s", new_columns)
    logger.info("Total missing values: %d", total_missing)
    logger.info("Memory usage: %.4f MB", memory_usage_mb)
    logger.info("Output path: %s", saved_path)
    logger.info("=========================================")

    print("=" * 60)
    print("Investor Feature Engineering -- Final Summary")
    print("=" * 60)
    print(f"Rows                  : {len(engineered_df)}")
    print(f"Columns               : {engineered_df.shape[1]}")
    print(f"Original feature count: {original_df.shape[1]}")
    print(f"New feature count     : {len(new_columns)}")
    print(f"Engineered features   : {new_columns}")
    print(f"Missing values        : {total_missing}")
    print(f"Memory usage (MB)     : {memory_usage_mb:.4f}")
    print(f"Saved to              : {saved_path}")
    print("=" * 60)


# ----------------------------------------------------------------------------
# Main Function
# ----------------------------------------------------------------------------
def main() -> None:
    """Run the full investor feature engineering pipeline end to end.

    Orchestrates: validate input file exists -> load -> validate
    dataset -> identify feature types -> create engineered features ->
    validate output dataset -> save -> summarize. Aborts early if the
    input file is missing, the dataset fails validation, or the
    engineered output fails post-validation.
    """
    logger.info("Starting investor feature engineering pipeline.")

    if not validate_input_file():
        logger.error("Aborting: required input file is missing.")
        return

    df = load_dataset(INPUT_FILEPATH)

    if df is None or not validate_dataset(df):
        logger.error("Aborting: dataset could not be loaded or failed validation.")
        return

    identify_feature_types(df)

    engineered_df = create_engineered_features(df)

    if not validate_output_dataset(df, engineered_df):
        logger.error("Aborting: engineered dataset failed output validation.")
        return

    saved_path = save_dataset(engineered_df, OUTPUT_FILEPATH)

    if saved_path is None:
        logger.error("Aborting: failed to save engineered dataset.")
        return

    summarize_dataset(df, engineered_df, saved_path)
    logger.info("Investor feature engineering pipeline complete. Saved: %s", saved_path)
    

# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    setup_logger()
    main()
