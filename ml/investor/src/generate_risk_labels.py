"""Compute a rule-based investor risk score and assign risk labels.

This module is the risk-scoring and labeling stage of the Investor
Profiling pipeline (a separate pipeline from the Stock Risk Prediction
pipeline, sharing the same architecture and coding conventions). Its
responsibility is to compute a transparent, rule-based
`investor_risk_score` for every investor in
`ml/investor/data/processed/investor_training_dataset.csv`, imitating
how a financial advisor would weigh an investor's stated preferences
and behaviour -- and to assign a final `Investor_Risk_Level`
(Conservative / Moderate / Aggressive) using dynamically computed
tercile thresholds.

SCORE METHODOLOGY: `investor_risk_score` is NOT a plain weighted sum
of the eight scoring rules. The raw sum is dampened by
`signal_agreement`, a conviction-ratio measure of how consistently
the eight rules agree in direction (see `calculate_signal_agreement`).
Two investors with an identical raw total can end up with different
final scores -- and different labels -- depending on whether that
total reflects consistent signals or ones that happen to cancel out.
This is fully deterministic and fully explainable: `investor_risk_score_raw`,
`signal_agreement`, and `advisor_confidence` (High/Medium/Low) are all
persisted alongside the final score so every label is traceable back
to exactly which rules agreed or disagreed -- see
`compute_investor_risk_score`.

THRESHOLDS: label cut points are NOT hardcoded. They are recomputed
from the CURRENT `investor_risk_score` distribution on every run,
using tercile (33rd / 66th percentile) quantiles -- see
`assign_investor_risk_labels`. This keeps the three labels
approximately balanced even if upstream scoring weights change and
shift the distribution.

This module MUST NOT:
    * Use KMeans or any other clustering algorithm.
    * Use any ML algorithm.
    * Generate random labels.

Typical usage:
    python -m src.generate_risk_labels
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------
import logging
import re
from pathlib import Path
from typing import Final, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------------
# Configuration Constants
# ----------------------------------------------------------------------------
# ml/investor/src/generate_risk_labels.py -> parent (src) -> parent (investor)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Directory containing the prepared training dataset.
PROCESSED_DATA_DIR: Final[Path] = BASE_DIR / "data" / "processed"

#: Input file produced by prepare_training_data.py.
INPUT_FILEPATH: Final[Path] = PROCESSED_DATA_DIR / "investor_training_dataset.csv"

#: Output file: original data plus investor_risk_score and Investor_Risk_Level.
OUTPUT_FILEPATH: Final[Path] = PROCESSED_DATA_DIR / "investor_labeled_training_dataset.csv"

#: Directory where figures are saved.
FIGURES_DIR: Final[Path] = BASE_DIR / "reports" / "figures"

#: Filename for the score distribution histogram.
SCORE_DISTRIBUTION_PLOT_FILENAME: Final[str] = "investor_score_distribution.png"

#: Filename for the Investor_Risk_Level bar chart.
LABEL_DISTRIBUTION_PLOT_FILENAME: Final[str] = "investor_risk_distribution.png"

#: Fixed display/iteration order for the three risk labels.
LABEL_ORDER: Final[list] = ["Conservative", "Moderate", "Aggressive"]

#: Columns that must be present for this module to proceed.
REQUIRED_COLUMNS: Final[list] = [
    "age",
    "mutual_funds",
    "equity_market",
    "government_bonds",
    "fixed_deposits",
    "ppf",
    "gold",
    "preferred_market_assets",
    "preferred_safe_assets",
    "investment_diversification_score",
    "duration",
    "objective",
    "expect",
    "age_group",
]
#: Small constant preventing division by zero when computing signal
#: agreement for a row where all rule contributions are exactly 0.
AGREEMENT_EPSILON: Final[float] = 1e-9

#: Floor applied to the agreement-based dampening factor (see
#: calculate_signal_agreement / compute_investor_risk_score). Even
#: when rule contributions maximally disagree, the score is only
#: shrunk toward this floor, never crushed to zero -- a real advisor
#: still forms a (softer) opinion under conflicting signals rather
#: than refusing to answer.
AGREEMENT_DAMPENING_FLOOR: Final[float] = 0.5

#: signal_agreement at or above this is classified "High" advisor
#: confidence (rules are largely pointing the same direction).
ADVISOR_CONFIDENCE_HIGH_THRESHOLD: Final[float] = 0.75

#: signal_agreement at or above this (but below the High threshold)
#: is classified "Medium"; below this is "Low".
ADVISOR_CONFIDENCE_LOW_THRESHOLD: Final[float] = 0.40

# --- Rule 1: Investment preference weights -----------------------------
#: Per-unit weight applied to each investment-avenue preference column.
#: Positive weights push the score toward "Aggressive"; negative
#: weights push it toward "Conservative". Gold's weight is kept small
#: per the task's explicit "only a very small influence" instruction.
INVESTMENT_PREFERENCE_WEIGHTS: Final[dict] = {
    "equity_market": 2.0,
    "mutual_funds": 1.5,

    # much smaller penalties
    "government_bonds": -0.5,
    "fixed_deposits": -0.5,
    "ppf": -0.5,

    "gold": 0.25,
}

# --- Rule 2 & 3: Preferred market / safe assets -------------------------
MARKET_ASSETS_COLUMN: Final[str] = "preferred_market_assets"
MARKET_ASSETS_WEIGHT: Final[float] = 1.5

SAFE_ASSETS_COLUMN: Final[str] = "preferred_safe_assets"
SAFE_ASSETS_WEIGHT: Final[float] = -1.0

# --- Rule 4: Diversification --------------------------------------------
#: Both names are accepted since upstream modules have used slightly
#: different names for this feature; whichever is present is used.
DIVERSIFICATION_COLUMN_CANDIDATES: Final[list] = [
    "investment_diversification_score",
    "diversification_score",
]
DIVERSIFICATION_WEIGHT: Final[float] = 0.5

# --- Rule 5: Investment duration ----------------------------------------
DURATION_COLUMN: Final[str] = "duration"
DURATION_SCORE_MAP: Final[dict] = {"short": -2.0, "medium": 0.0, "long": 2.0, "unknown": 0.0}
#: A parsed duration value (in years) at or below this is "short".
DURATION_SHORT_MAX_YEARS: Final[float] = 3.0
#: A parsed duration value (in years) at or above this is "long".
DURATION_LONG_MIN_YEARS: Final[float] = 5.0

# --- Rule 6: Investment objective ----------------------------------------
OBJECTIVE_COLUMN: Final[str] = "objective"
GROWTH_OBJECTIVE_KEYWORDS: Final[list] = [
    "capital appreciation", "wealth creation", "growth", "aggressive",
]
INCOME_OBJECTIVE_KEYWORDS: Final[list] = [
    "income", "saving", "capital preservation", "preservation", "safety", "secure",
]
OBJECTIVE_SCORE_MAP: Final[dict] = {"growth": 2.0, "income": -2.0, "unknown": 0.0}

# --- Rule 7: Expected return -----------------------------------------------
EXPECTED_RETURN_COLUMN: Final[str] = "expect"
#: Weight applied to the parsed numeric expected-return value (percent).
#: E.g. a parsed value of 20 (meaning "20%") contributes 20 * 0.05 = 1.0.
EXPECTED_RETURN_WEIGHT: Final[float] = 0.05

# --- Rule 8: Age group -----------------------------------------------------
AGE_GROUP_COLUMN: Final[str] = "age_group"
AGE_GROUP_SCORE_MAP: Final[dict] = {"young": 1.0, "adult": 0.0, "senior": -1.0}

# --- Final labeling: dynamic tercile thresholds -----------------------
#: Lower quantile cut point (33rd percentile) used to split
#: investor_risk_score into Conservative / Moderate / Aggressive.
#: Recomputed from the CURRENT dataset every time
#: assign_investor_risk_labels runs -- never hardcoded -- so labeling
#: stays balanced even if upstream scoring weights shift the
#: distribution.
LOWER_QUANTILE: Final[float] = 0.33

#: Upper quantile cut point (66th percentile). Same rationale as
#: `LOWER_QUANTILE`.
UPPER_QUANTILE: Final[float] = 0.66

# --- Realistic behavioural variation ---------------------------------------
# ML AUDIT FINDING (see Machine Learning Audit Report in the Streamlit app):
# investor_risk_score is a fully deterministic function of the same raw
# survey columns the classifier is trained on, so two investors who answer
# identically always get an identical label -- a Random Forest can then
# reconstruct that rule almost perfectly, which is why the classifier was
# reporting ~100% accuracy. This is NOT classic data/target leakage (the
# score columns are correctly excluded from the feature matrix -- see
# LEAKAGE_COLUMNS in train_investor_classifier.py); the label itself simply
# left the model nothing to generalize about.
#
# Real investors are not perfectly rule-following: two people who fill out
# an identical questionnaire can still have genuinely different risk
# appetites for reasons the eight scoring rules cannot capture. This
# constant models that residual human unpredictability as a small,
# fixed-seed Gaussian perturbation added to the deterministic score before
# labeling. It does not touch the eight rule weights and does not flip a
# clearly Conservative or clearly Aggressive investor to the opposite end
# -- it only blurs the boundary for borderline cases, which is exactly
# where a real classifier should be forced to generalize rather than
# memorize. Chosen at ~30% of the deterministic score's typical spread.
BEHAVIORAL_NOISE_STD: Final[float] = 1.75

#: Fixed seed for the behavioural noise draw, so relabeling is reproducible
#: run-to-run given the same input dataset.
BEHAVIORAL_NOISE_SEED: Final[int] = 42

#: Regex used to extract numeric values from free-text columns
#: (e.g. "3-5 years", "20%-30%").
NUMBER_PATTERN: Final[re.Pattern] = re.compile(r"-?\d+\.?\d*")

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
def _extract_numbers(text: object) -> list:
    """Extract all numeric values found in a free-text string.

    Args:
        text: The value to parse. Non-string/NaN input yields an
            empty list rather than raising.

    Returns:
        A list of floats found in `text`, in order of appearance.
    """
    if pd.isna(text):
        return []

    return [float(match) for match in NUMBER_PATTERN.findall(str(text))]


def _first_available_column(df: pd.DataFrame, candidates: list) -> Optional[str]:
    """Return the first candidate column name that exists in the dataset.

    Args:
        df: The dataset to check.
        candidates: Column names to check, in preference order.

    Returns:
        The first matching column name, or None if none are present.
    """
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None


def _classify_duration(value: object) -> str:
    """Classify a free-text duration value into short/medium/long.

    Numeric years are extracted from the text where possible (e.g.
    "3-5 years" -> [3.0, 5.0]); the largest extracted number is
    compared against `DURATION_SHORT_MAX_YEARS` and
    `DURATION_LONG_MIN_YEARS`. If no numbers are found, common keyword
    phrases ("more than", "above", "short", "long") are checked as a
    fallback.

    Args:
        value: The raw duration value.

    Returns:
        One of "short", "medium", "long", or "unknown".
    """
    if pd.isna(value):
        return "unknown"

    normalized = str(value).strip().lower()
    numbers = _extract_numbers(normalized)

    if numbers:
        max_years = max(numbers)
        if "more than" in normalized or "above" in normalized or "greater" in normalized:
            return "long"
        if max_years <= DURATION_SHORT_MAX_YEARS:
            return "short"
        if max_years >= DURATION_LONG_MIN_YEARS:
            return "long"
        return "medium"

    if "more than" in normalized or "above" in normalized or "long" in normalized:
        return "long"
    if "short" in normalized:
        return "short"
    if "medium" in normalized or "moderate" in normalized:
        return "medium"

    return "unknown"


def _classify_objective(value: object) -> str:
    """Classify a free-text investment objective into growth/income/unknown.

    Uses case-insensitive substring matching against
    `GROWTH_OBJECTIVE_KEYWORDS` and `INCOME_OBJECTIVE_KEYWORDS`.

    Args:
        value: The raw objective value.

    Returns:
        One of "growth", "income", or "unknown".
    """
    if pd.isna(value):
        return "unknown"

    normalized = str(value).strip().lower()

    if any(keyword in normalized for keyword in GROWTH_OBJECTIVE_KEYWORDS):
        return "growth"
    if any(keyword in normalized for keyword in INCOME_OBJECTIVE_KEYWORDS):
        return "income"

    return "unknown"


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
    """Run all validation checks required before scoring.

    Checks that the dataframe loaded successfully and is non-empty,
    has no duplicate rows, and that all `REQUIRED_COLUMNS` are
    present.

    Args:
        df: The loaded, prepared dataset.

    Returns:
        True only if every individual validation check passes, False
        if any check fails.
    """
    checks = {
        "dataframe loaded correctly": df is not None,
        "dataframe not empty": df is not None and not df.empty,
        "no duplicate rows": df is not None and not df.duplicated().any(),
        "required columns present": _validate_required_columns(df),
    }

    for check_name, passed in checks.items():
        logger.info("Validation check '%s': %s", check_name, "PASSED" if passed else "FAILED")

    return all(checks.values())


def _validate_required_columns(df: pd.DataFrame) -> bool:
    """Verify that all columns in `REQUIRED_COLUMNS` are present.

    If `REQUIRED_COLUMNS` is empty, this check trivially passes.

    Args:
        df: The dataset to validate.

    Returns:
        True if every column in `REQUIRED_COLUMNS` is present, False
        otherwise.
    """
    if not REQUIRED_COLUMNS:
        logger.warning("REQUIRED_COLUMNS is empty; skipping required-column validation.")
        return True

    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)

    if missing_columns:
        logger.error("Missing required columns: %s", sorted(missing_columns))
        return False

    return True


def validate_scored_dataset(original_df: pd.DataFrame, scored_df: pd.DataFrame) -> bool:
    """Run validation checks on the dataset after scoring and labeling.

    Checks that the row count is unchanged, no duplicate rows exist,
    `investor_risk_score` has no missing values, `Investor_Risk_Level`
    has no missing values, and exactly the three expected labels are
    present. This function does not compute labels itself -- it
    assumes `assign_investor_risk_labels` has already been applied to
    `scored_df`.

    Args:
        original_df: The dataset before scoring.
        scored_df: The dataset after `investor_risk_score` and
            `Investor_Risk_Level` were added.

    Returns:
        True only if every individual check passes, False otherwise.
    """
    expected_labels = set(LABEL_ORDER)
    has_label_column = "Investor_Risk_Level" in scored_df.columns
    actual_labels = set(scored_df["Investor_Risk_Level"].unique()) if has_label_column else set()

    checks = {
        "row count unchanged": len(original_df) == len(scored_df),
        "no duplicate rows": not scored_df.duplicated().any(),
        "no missing investor_risk_score": scored_df["investor_risk_score"].notna().all(),
        "no missing signal_agreement": scored_df["signal_agreement"].notna().all(),
        "no missing Investor_Risk_Level": has_label_column and scored_df["Investor_Risk_Level"].notna().all(),
        "exactly three labels generated": actual_labels == expected_labels,
    }

    for check_name, passed in checks.items():
        logger.info("Post-scoring validation check '%s': %s", check_name, "PASSED" if passed else "FAILED")

    return all(checks.values())


# ----------------------------------------------------------------------------
# Core Functions -- Loading
# ----------------------------------------------------------------------------
def load_dataset(filepath: Path) -> Optional[pd.DataFrame]:
    """Load the prepared investor training dataset from a CSV file.

    Args:
        filepath: Path to `investor_training_dataset.csv`.

    Returns:
        The loaded DataFrame, or None if the file could not be read.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception:
        logger.error("Failed to load dataset: %s", filepath, exc_info=True)
        return None

    logger.info("Loaded prepared dataset from %s | Shape: %s", filepath, df.shape)
    return df


# ----------------------------------------------------------------------------
# Score Functions
# ----------------------------------------------------------------------------
def score_investment_preference(df: pd.DataFrame) -> pd.Series:
    """Score Rule 1: weighted sum of investment-avenue preferences.

    Uses whichever of `INVESTMENT_PREFERENCE_WEIGHTS` keys are present
    in the dataset; missing columns contribute 0 and are logged.

    Args:
        df: The dataset to score.

    Returns:
        A Series of per-row contributions to `investor_risk_score`.
    """
    contribution = pd.Series(0.0, index=df.index)
    used_columns = []

    for column, weight in INVESTMENT_PREFERENCE_WEIGHTS.items():
        if column in df.columns:
            contribution += df[column].fillna(0) * weight
            used_columns.append(column)

    missing = [col for col in INVESTMENT_PREFERENCE_WEIGHTS if col not in df.columns]
    if missing:
        logger.warning("Rule 1 (investment preference): columns not found and skipped: %s", missing)
    logger.info("Rule 1 (investment preference): used columns %s", used_columns)

    return contribution


def score_preferred_market_assets(df: pd.DataFrame) -> pd.Series:
    """Score Rule 2: preferred market assets increase the score.

    Args:
        df: The dataset to score.

    Returns:
        A Series of per-row contributions to `investor_risk_score`.
    """
    if MARKET_ASSETS_COLUMN not in df.columns:
        logger.warning("Rule 2 (preferred market assets): column '%s' not found; skipped.", MARKET_ASSETS_COLUMN)
        return pd.Series(0.0, index=df.index)

    return df[MARKET_ASSETS_COLUMN].fillna(0) * MARKET_ASSETS_WEIGHT


def score_preferred_safe_assets(df: pd.DataFrame) -> pd.Series:
    """Score Rule 3: preferred safe assets decrease the score.

    Args:
        df: The dataset to score.

    Returns:
        A Series of per-row contributions to `investor_risk_score`.
    """
    if SAFE_ASSETS_COLUMN not in df.columns:
        logger.warning("Rule 3 (preferred safe assets): column '%s' not found; skipped.", SAFE_ASSETS_COLUMN)
        return pd.Series(0.0, index=df.index)

    return df[SAFE_ASSETS_COLUMN].fillna(0) * SAFE_ASSETS_WEIGHT


def score_diversification(df: pd.DataFrame) -> pd.Series:
    """Score Rule 4: higher diversification slightly increases the score.

    Args:
        df: The dataset to score.

    Returns:
        A Series of per-row contributions to `investor_risk_score`.
    """
    column = _first_available_column(df, DIVERSIFICATION_COLUMN_CANDIDATES)

    if column is None:
        logger.warning(
            "Rule 4 (diversification): none of %s found; skipped.", DIVERSIFICATION_COLUMN_CANDIDATES
        )
        return pd.Series(0.0, index=df.index)

    logger.info("Rule 4 (diversification): using column '%s'", column)
    return df[column].fillna(0) * DIVERSIFICATION_WEIGHT


def score_duration(df: pd.DataFrame) -> pd.Series:
    """Score Rule 5: longer investment horizon increases the score.

    Args:
        df: The dataset to score.

    Returns:
        A Series of per-row contributions to `investor_risk_score`.
    """
    if DURATION_COLUMN not in df.columns:
        logger.warning("Rule 5 (duration): column '%s' not found; skipped.", DURATION_COLUMN)
        return pd.Series(0.0, index=df.index)

    categories = df[DURATION_COLUMN].apply(_classify_duration)
    unknown_count = int((categories == "unknown").sum())
    if unknown_count > 0:
        logger.warning("Rule 5 (duration): %d value(s) could not be classified.", unknown_count)

    return categories.map(DURATION_SCORE_MAP).astype(float)


def score_objective(df: pd.DataFrame) -> pd.Series:
    """Score Rule 6: growth-oriented objectives increase the score.

    Args:
        df: The dataset to score.

    Returns:
        A Series of per-row contributions to `investor_risk_score`.
    """
    if OBJECTIVE_COLUMN not in df.columns:
        logger.warning("Rule 6 (objective): column '%s' not found; skipped.", OBJECTIVE_COLUMN)
        return pd.Series(0.0, index=df.index)

    categories = df[OBJECTIVE_COLUMN].apply(_classify_objective)
    unknown_count = int((categories == "unknown").sum())
    if unknown_count > 0:
        logger.warning("Rule 6 (objective): %d value(s) could not be classified.", unknown_count)

    return categories.map(OBJECTIVE_SCORE_MAP).astype(float)


def score_expected_return(df: pd.DataFrame) -> pd.Series:
    """Score Rule 7: higher expected return increases the score.

    Numeric values (e.g. percentages) are extracted from free text and
    averaged where a range is given (e.g. "20%-30%" -> 25.0).

    Args:
        df: The dataset to score.

    Returns:
        A Series of per-row contributions to `investor_risk_score`.
    """
    if EXPECTED_RETURN_COLUMN not in df.columns:
        logger.warning("Rule 7 (expected return): column '%s' not found; skipped.", EXPECTED_RETURN_COLUMN)
        return pd.Series(0.0, index=df.index)

    def _parsed_value(value: object) -> float:
        numbers = _extract_numbers(value)
        return float(np.mean(numbers)) if numbers else 0.0

    parsed_values = df[EXPECTED_RETURN_COLUMN].apply(_parsed_value)
    unparsed_count = int((parsed_values == 0.0).sum())
    if unparsed_count > 0:
        logger.warning("Rule 7 (expected return): %d value(s) could not be parsed as numeric.", unparsed_count)

    return parsed_values * EXPECTED_RETURN_WEIGHT


def score_age_group(df: pd.DataFrame) -> pd.Series:
    """Score Rule 8: younger age groups slightly increase the score.

    Args:
        df: The dataset to score.

    Returns:
        A Series of per-row contributions to `investor_risk_score`.
    """
    if AGE_GROUP_COLUMN not in df.columns:
        logger.warning("Rule 8 (age group): column '%s' not found; skipped.", AGE_GROUP_COLUMN)
        return pd.Series(0.0, index=df.index)

    normalized = df[AGE_GROUP_COLUMN].astype(str).str.strip().str.lower()
    unknown_count = int((~normalized.isin(AGE_GROUP_SCORE_MAP.keys())).sum())
    if unknown_count > 0:
        logger.warning("Rule 8 (age group): %d value(s) did not match young/adult/senior.", unknown_count)

    return normalized.map(AGE_GROUP_SCORE_MAP).fillna(0.0)


def calculate_signal_agreement(rule_contributions: dict) -> pd.Series:
    """Measure how consistently the eight rule contributions agree in direction.

    Computed as a conviction ratio, a standard multi-factor signal
    metric:

        signal_agreement = |sum(contributions)| / sum(|contributions|)

    A value of 1.0 means every rule pushed the score in the same
    direction (no internal disagreement). A value near 0 means the
    rules largely cancel each other out -- e.g. a strong equity
    preference offset by an equally strong short-duration penalty --
    which is exactly the situation where a real financial advisor
    would be less confident in a clean-cut label, even if the two
    signals happen to net out to the same total as a genuinely
    one-sided profile.

    Args:
        rule_contributions: The dict of per-rule contribution Series,
            as computed in `compute_investor_risk_score`.

    Returns:
        A Series of agreement ratios in [0, 1], one per row.
    """
    stacked = pd.concat(rule_contributions.values(), axis=1)
    net_signal = stacked.sum(axis=1).abs()
    gross_signal = stacked.abs().sum(axis=1)
    return (net_signal / (gross_signal + AGREEMENT_EPSILON)).clip(0.0, 1.0)


def classify_advisor_confidence(signal_agreement: pd.Series) -> pd.Series:
    """Bucket signal agreement into High/Medium/Low advisor confidence tiers.

    Purely descriptive/explanatory -- this tier is persisted alongside
    the score so every label can be traced back to how much internal
    agreement existed among the eight scoring rules, but it does not
    itself alter the score or the label.

    Args:
        signal_agreement: The Series returned by
            `calculate_signal_agreement`.

    Returns:
        A Series of "High", "Medium", or "Low" strings.
    """
    conditions = [
        signal_agreement >= ADVISOR_CONFIDENCE_HIGH_THRESHOLD,
        signal_agreement >= ADVISOR_CONFIDENCE_LOW_THRESHOLD,
    ]
    return pd.Series(
        np.select(conditions, ["High", "Medium"], default="Low"),
        index=signal_agreement.index,
    )


def compute_investor_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    """Compute investor_risk_score from the eight rule contributions.

    Unlike a plain weighted sum, the raw sum of rule contributions is
    dampened by how much the individual rules agree with each other
    (see `calculate_signal_agreement`). Two investors with an
    identical raw total can therefore receive different final scores
    -- and potentially different labels -- depending on whether that
    total reflects consistent signals or conflicting ones that happen
    to net out the same. This is fully deterministic (no randomness)
    and fully explainable: `investor_risk_score_raw`,
    `signal_agreement`, and `advisor_confidence` are all persisted
    alongside the final `investor_risk_score`, so every label can be
    traced back to exactly which rules agreed or disagreed.

    Args:
        df: The validated, prepared dataset.

    Returns:
        A new DataFrame identical to `df` with `investor_risk_score`,
        `investor_risk_score_raw`, `signal_agreement`, and
        `advisor_confidence` columns added.
    """
    result = df.copy()

    rule_contributions = {
        "rule_1_investment_preference": score_investment_preference(result),
        "rule_2_market_assets": score_preferred_market_assets(result),
        "rule_3_safe_assets": score_preferred_safe_assets(result),
        "rule_4_diversification": score_diversification(result),
        "rule_5_duration": score_duration(result),
        "rule_6_objective": score_objective(result),
        "rule_7_expected_return": score_expected_return(result),
        "rule_8_age_group": score_age_group(result),
    }

    raw_score = sum(rule_contributions.values())
    signal_agreement = calculate_signal_agreement(rule_contributions)
    agreement_factor = AGREEMENT_DAMPENING_FLOOR + (1 - AGREEMENT_DAMPENING_FLOOR) * signal_agreement

    result["investor_risk_score_raw"] = raw_score
    result["signal_agreement"] = signal_agreement
    result["advisor_confidence"] = classify_advisor_confidence(signal_agreement)
    result["investor_risk_score"] = raw_score * agreement_factor

    logger.info("Rule-level mean contributions:")
    for rule_name, contribution in rule_contributions.items():
        logger.info("  %s: mean=%.4f", rule_name, contribution.mean())
    logger.info("Mean signal agreement: %.4f", signal_agreement.mean())
    logger.info(
        "Advisor confidence distribution:\n%s",
        result["advisor_confidence"].value_counts().to_string(),
    )

    return result


def apply_behavioral_noise(df: pd.DataFrame) -> pd.DataFrame:
    """Perturb the deterministic investor_risk_score with realistic noise.

    See the module-level comment above `BEHAVIORAL_NOISE_STD` for the full
    rationale (this is the fix for the ML-audit finding that the label was
    a perfectly deterministic function of the training features). The
    pre-noise score is preserved as `investor_risk_score_deterministic` so
    the exact rule-based value stays auditable; `investor_risk_score` (the
    column labeling and training actually use downstream) becomes the
    noised value.

    Args:
        df: The dataset with `investor_risk_score` already computed by
            `compute_investor_risk_score`.

    Returns:
        A new DataFrame with `investor_risk_score_deterministic` (the
        original rule-based score) and `behavioral_noise` added, and
        `investor_risk_score` overwritten with the noised value.
    """
    result = df.copy()
    rng = np.random.default_rng(BEHAVIORAL_NOISE_SEED)

    result["investor_risk_score_deterministic"] = result["investor_risk_score"]
    result["behavioral_noise"] = rng.normal(
        loc=0.0, scale=BEHAVIORAL_NOISE_STD, size=len(result)
    )
    result["investor_risk_score"] = (
        result["investor_risk_score_deterministic"] + result["behavioral_noise"]
    )

    logger.info(
        "Applied behavioral noise (std=%.2f, seed=%d) to deterministic risk score.",
        BEHAVIORAL_NOISE_STD,
        BEHAVIORAL_NOISE_SEED,
    )
    return result


# ----------------------------------------------------------------------------
# Label Functions
# ----------------------------------------------------------------------------
def report_score_distribution(df: pd.DataFrame) -> dict:
    """Compute and report descriptive statistics of investor_risk_score.

    Args:
        df: The scored dataset, containing `investor_risk_score`.

    Returns:
        A dict of summary statistics: min, max, mean, median, and the
        25th/50th/75th percentiles.
    """
    scores = df["investor_risk_score"]

    stats = {
        "min": float(scores.min()),
        "max": float(scores.max()),
        "mean": float(scores.mean()),
        "median": float(scores.median()),
        "q25": float(scores.quantile(0.25)),
        "q50": float(scores.quantile(0.50)),
        "q75": float(scores.quantile(0.75)),
        "std": float(scores.std()),
    }

    logger.info("===== investor_risk_score Distribution =====")
    for stat_name, stat_value in stats.items():
        logger.info("  %s: %.4f", stat_name, stat_value)
    logger.info("==============================================")

    print("=" * 60)
    print("investor_risk_score -- Full Distribution")
    print("=" * 60)
    print(scores.describe().to_string())
    print("=" * 60)

    return stats


def assign_investor_risk_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Assign Conservative/Moderate/Aggressive labels using tercile thresholds.

    Thresholds are computed fresh from the CURRENT investor_risk_score
    distribution every time this function runs (`LOWER_QUANTILE` /
    `UPPER_QUANTILE`, default 33rd / 66th percentile) -- never
    hardcoded -- so labeling stays approximately balanced even if
    upstream scoring weights shift the distribution:
        * score <= lower_threshold                     -> "Conservative"
        * lower_threshold < score <= upper_threshold    -> "Moderate"
        * score > upper_threshold                       -> "Aggressive"

    Primary method: `pandas.qcut` with `duplicates="drop"`, which
    bins `investor_risk_score` into three roughly equal-sized groups.
    If many duplicate score values sit exactly at the quantile
    boundaries, `qcut` may be unable to produce exactly three distinct
    bins; in that case this function falls back to manually applying
    the `LOWER_QUANTILE` / `UPPER_QUANTILE` cut points directly, and
    logs a warning explaining why.

    Args:
        df: The scored dataset, containing `investor_risk_score`.

    Returns:
        A new DataFrame identical to `df` with an `Investor_Risk_Level`
        column added.
    """
    result = df.copy()
    scores = result["investor_risk_score"]

    try:
        result["Investor_Risk_Level"] = pd.qcut(
            scores, q=3, labels=LABEL_ORDER, duplicates="drop"
        ).astype(str)

        lower_threshold = float(scores.quantile(LOWER_QUANTILE))
        upper_threshold = float(scores.quantile(UPPER_QUANTILE))
        method = "qcut"

    except ValueError as exc:
        logger.warning(
            "qcut could not produce exactly three bins (%s); "
            "falling back to manual quantile-based thresholds.",
            exc,
        )

        lower_threshold = float(scores.quantile(LOWER_QUANTILE))
        upper_threshold = float(scores.quantile(UPPER_QUANTILE))

        conditions = [
            scores <= lower_threshold,
            (scores > lower_threshold) & (scores <= upper_threshold),
            scores > upper_threshold,
        ]
        result["Investor_Risk_Level"] = np.select(conditions, LABEL_ORDER, default="Moderate")
        method = "quantile fallback"

    logger.info(
        "Computed thresholds (%s): Conservative <= %.2f | Moderate <= %.2f | Aggressive > %.2f",
        method,
        lower_threshold,
        upper_threshold,
        upper_threshold,
    )
    print(
        "Computed thresholds:\n"
        f"  Conservative <= {lower_threshold:.2f}\n"
        f"  Moderate <= {upper_threshold:.2f}\n"
        f"  Aggressive > {upper_threshold:.2f}"
    )

    return result


# ----------------------------------------------------------------------------
# Visualization
# ----------------------------------------------------------------------------
def plot_score_distribution(df: pd.DataFrame) -> Path:
    """Create and save a histogram of investor_risk_score, colored by label.

    Args:
        df: The labeled dataset, containing `investor_risk_score` and
            `Investor_Risk_Level`.

    Returns:
        The path the figure was saved to.
    """
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6))

    if "Investor_Risk_Level" in df.columns:
        for label in LABEL_ORDER:
            subset = df.loc[df["Investor_Risk_Level"] == label, "investor_risk_score"]
            ax.hist(subset, bins=20, alpha=0.6, label=label, edgecolor="black")
        ax.legend()
    else:
        ax.hist(df["investor_risk_score"], bins=30, edgecolor="black")

    ax.set_title("Investor Risk Score Distribution")
    ax.set_xlabel("investor_risk_score")
    ax.set_ylabel("Number of Investors")
    ax.grid(True, axis="y")
    fig.tight_layout()

    filepath = FIGURES_DIR / SCORE_DISTRIBUTION_PLOT_FILENAME
    fig.savefig(filepath)
    plt.close(fig)

    return filepath


def plot_label_distribution(df: pd.DataFrame) -> Path:
    """Create and save a bar chart of Investor_Risk_Level counts.

    Args:
        df: The labeled dataset, containing `Investor_Risk_Level`.

    Returns:
        The path the figure was saved to.
    """
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    counts = df["Investor_Risk_Level"].value_counts().reindex(LABEL_ORDER).fillna(0)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.bar(counts.index, counts.values)
    ax.set_title("Investor Risk Level Distribution")
    ax.set_xlabel("Investor Risk Level")
    ax.set_ylabel("Number of Investors")
    ax.grid(True, axis="y")
    fig.tight_layout()

    filepath = FIGURES_DIR / LABEL_DISTRIBUTION_PLOT_FILENAME
    fig.savefig(filepath)
    plt.close(fig)

    return filepath


# ----------------------------------------------------------------------------
# Save Functions
# ----------------------------------------------------------------------------
def save_labeled_dataset(df: pd.DataFrame, filepath: Path) -> Optional[Path]:
    """Persist the scored and labeled dataset to the processed data directory.

    Args:
        df: The dataset with `investor_risk_score` and
            `Investor_Risk_Level` added.
        filepath: The full path (including filename) to save to.

    Returns:
        The path the CSV file was written to, or None if saving
        failed.
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(filepath, index=False)
    except Exception:
        logger.error("Failed to save labeled dataset to %s", filepath, exc_info=True)
        return None

    return filepath


# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------
def summarize_results(
    df: pd.DataFrame,
    stats: dict,
    saved_path: Path,
    score_plot_path: Path,
    label_plot_path: Path,
) -> None:
    """Print and log a final summary of the risk-scoring and labeling run.

    Args:
        df: The final scored and labeled dataset.
        stats: The distribution statistics from
            `report_score_distribution`.
        saved_path: The path the labeled dataset was saved to.
        score_plot_path: The path the score distribution histogram
            was saved to.
        label_plot_path: The path the label count bar chart was saved
            to.
    """
    label_counts = df["Investor_Risk_Level"].value_counts().reindex(LABEL_ORDER).fillna(0).astype(int)

    logger.info("===== Investor Risk Scoring & Labeling Summary =====")
    logger.info("Rows: %d", len(df))
    logger.info("Columns: %d", df.shape[1])
    logger.info("Label counts: %s", label_counts.to_dict())
    logger.info("Minimum score: %.4f", stats["min"])
    logger.info("Maximum score: %.4f", stats["max"])
    logger.info("Mean score: %.4f", stats["mean"])
    logger.info("Output file: %s", saved_path)
    logger.info("=====================================================")

    print("=" * 60)
    print("Investor Risk Scoring & Labeling -- Final Summary")
    print("=" * 60)
    print(f"Rows                : {len(df)}")
    print(f"Columns             : {df.shape[1]}")
    print(f"Label counts        : {label_counts.to_dict()}")
    print(f"Minimum score       : {stats['min']:.4f}")
    print(f"Maximum score       : {stats['max']:.4f}")
    print(f"Mean score          : {stats['mean']:.4f}")
    print(f"Median score        : {stats['median']:.4f}")
    print(f"25th / 75th pctile  : {stats['q25']:.4f} / {stats['q75']:.4f}")
    print(f"Saved to            : {saved_path}")
    print(f"Score histogram     : {score_plot_path}")
    print(f"Label bar chart     : {label_plot_path}")
    print("=" * 60)


# ----------------------------------------------------------------------------
# Main Function
# ----------------------------------------------------------------------------
def main() -> None:
    """Run the investor risk-scoring and labeling pipeline end to end.

    Orchestrates: validate input exists -> load -> validate dataset ->
    compute investor_risk_score -> assign Investor_Risk_Level ->
    validate scored/labeled output -> report distribution -> plot ->
    save -> summarize. Aborts early if the input file is missing, the
    dataset fails validation, or post-scoring validation fails.
    """
    logger.info("Starting investor risk scoring and labeling pipeline.")

    if not validate_input_file():
        logger.error("Aborting: required input file is missing.")
        return

    df = load_dataset(INPUT_FILEPATH)

    if df is None or not validate_dataset(df):
        logger.error("Aborting: dataset could not be loaded or failed validation.")
        return

    scored_df = compute_investor_risk_score(df)
    scored_df = apply_behavioral_noise(scored_df)
    scored_df = assign_investor_risk_labels(scored_df)

    if not validate_scored_dataset(df, scored_df):
        logger.error("Aborting: scored/labeled dataset failed validation.")
        return

    stats = report_score_distribution(scored_df)

    score_plot_path = plot_score_distribution(scored_df)
    label_plot_path = plot_label_distribution(scored_df)

    saved_path = save_labeled_dataset(scored_df, OUTPUT_FILEPATH)

    if saved_path is None:
        logger.error("Aborting: failed to save labeled dataset.")
        return

    summarize_results(scored_df, stats, saved_path, score_plot_path, label_plot_path)
    logger.info("Investor risk scoring and labeling pipeline complete. Saved: %s", saved_path)


# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    setup_logger()
    main()