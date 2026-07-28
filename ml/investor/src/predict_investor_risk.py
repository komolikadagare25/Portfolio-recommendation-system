"""Predict an investor's risk level using the already-trained classifier.

This module is the inference stage of the Investor Profiling pipeline
(sharing the same architecture and coding conventions as the rest of
the pipeline). Its sole responsibility is to take a single investor's
raw survey answers (as a dict or a one-row DataFrame), validate them,
encode them using the already-fitted `OrdinalEncoder`, and return a
risk prediction using the already-trained `RandomForestClassifier`
and `LabelEncoder`.

This is the module the backend (Node.js/Express) integrates with, via
`predict_investor_risk(user_input)`. The backend never needs to know
about feature engineering, encoding, preprocessing, or feature
ordering -- all of that happens inside this module.

This module MUST NOT:
    * Retrain, fit, or tune the model.
    * Fit the OrdinalEncoder or LabelEncoder (only `.transform` /
      `.inverse_transform` are used).
    * Split any dataset.
    * Recompute investor_risk_score or any other leakage-adjacent
      feature (see LEAKAGE_COLUMNS in train_investor_classifier.py).

Typical usage:
    from src.predict_investor_risk import predict_investor_risk

    result = predict_investor_risk({
        "gender": "Female",
        "age": 24,
        ...
    })
    # {"risk_level": "Moderate", "confidence": 0.94}
"""

# ----------------------------------------------------------------------------
# 1. Imports
# ----------------------------------------------------------------------------
import logging
from pathlib import Path
from typing import Final, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder

# ----------------------------------------------------------------------------
# 2. Constants
# ----------------------------------------------------------------------------
# ml/investor/src/predict_investor_risk.py -> parent (src) -> parent (investor)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Directory holding the trained model and fitted encoders.
MODELS_DIR: Final[Path] = BASE_DIR / "models"

#: Trained classifier, produced by train_investor_classifier.py.
MODEL_FILEPATH: Final[Path] = MODELS_DIR / "investor_risk_classifier.pkl"

#: Fitted feature OrdinalEncoder, produced by train_investor_classifier.py.
ORDINAL_ENCODER_FILEPATH: Final[Path] = MODELS_DIR / "ordinal_encoder.pkl"

#: Fitted target LabelEncoder, produced by train_investor_classifier.py.
LABEL_ENCODER_FILEPATH: Final[Path] = MODELS_DIR / "label_encoder.pkl"

#: The exact 24 features the model was trained on, in the exact order
#: used during training. This is the authoritative fallback column
#: order if the loaded model has no `feature_names_in_` (e.g. an
#: older scikit-learn artifact fit on a plain numpy array).
FEATURE_COLUMNS: Final[list] = [
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

#: Numeric feature columns: age plus the seven 1-7 style investment
#: avenue preference ranks.
NUMERIC_COLUMNS: Final[list] = [
    "age",
    "mutual_funds",
    "equity_market",
    "debentures",
    "government_bonds",
    "fixed_deposits",
    "ppf",
    "gold",
]

#: Categorical (string) feature columns -- every FEATURE_COLUMNS entry
#: that is not in NUMERIC_COLUMNS. Used as a fallback if the loaded
#: OrdinalEncoder has no `feature_names_in_` attribute; the encoder's
#: own fitted column list is preferred when available (see
#: `encode_categorical_features`).
CATEGORICAL_COLUMNS: Final[list] = [col for col in FEATURE_COLUMNS if col not in NUMERIC_COLUMNS]

#: Columns that must NEVER be present in the input to this module --
#: leakage-adjacent columns generated internally by earlier pipeline
#: stages. Their presence indicates the caller is passing engineered
#: pipeline output instead of raw survey answers.
FORBIDDEN_COLUMNS: Final[list] = [
    "Investor_Risk_Level",
    "investor_risk_score",
    "investor_risk_score_raw",
    "signal_agreement",
    "advisor_confidence",
    "total_investment_score",
    "preferred_safe_assets",
    "preferred_market_assets",
    "investment_diversification_score",
    "age_group",
]

#: Logging verbosity for this module.
LOG_LEVEL: Final[int] = logging.INFO

# ----------------------------------------------------------------------------
# 3. Logger
# ----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def setup_logger() -> None:
    """Attach a basic stream handler to this module's logger.

    Configures the module-level logger with an INFO-level stream
    handler and a timestamped formatter. Applied only when the module
    is run as a script (see the entry point at the bottom of the
    file), so importing this module (e.g. from a backend service)
    does not silently attach handlers to the caller's logging
    configuration.
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
# 4. Validation Functions
# ----------------------------------------------------------------------------
def validate_artifact_files_exist() -> None:
    """Verify that the model and both encoders exist on disk.

    Raises:
        FileNotFoundError: If the model, ordinal encoder, or label
            encoder file is missing, naming exactly which one.
    """
    required_files = {
        "model": MODEL_FILEPATH,
        "ordinal encoder": ORDINAL_ENCODER_FILEPATH,
        "label encoder": LABEL_ENCODER_FILEPATH,
    }

    missing = [name for name, filepath in required_files.items() if not filepath.exists()]

    if missing:
        raise FileNotFoundError(
            f"Required artifact(s) not found: {missing}. "
            f"Expected paths: { {name: str(path) for name, path in required_files.items()} }"
        )


def validate_required_columns(df: pd.DataFrame) -> None:
    """Verify that every required feature column is present and no others.

    Args:
        df: The single-row input DataFrame to validate.

    Raises:
        ValueError: If any required column is missing, if any
            forbidden (leakage-adjacent) column is present, or if any
            unexpected column is present.
    """
    input_columns = set(df.columns)
    required_columns = set(FEATURE_COLUMNS)

    missing_columns = required_columns - input_columns
    if missing_columns:
        raise ValueError(f"Missing required column(s): {sorted(missing_columns)}")

    forbidden_present = input_columns & set(FORBIDDEN_COLUMNS)
    if forbidden_present:
        raise ValueError(
            f"Forbidden (leakage-adjacent) column(s) present: {sorted(forbidden_present)}. "
            "Only raw survey answers may be passed to predict_investor_risk()."
        )

    unexpected_columns = input_columns - required_columns
    if unexpected_columns:
        raise ValueError(f"Unexpected column(s) present: {sorted(unexpected_columns)}")


def validate_no_missing_values(df: pd.DataFrame) -> None:
    """Verify that no required feature value is missing.

    Args:
        df: The single-row input DataFrame to validate.

    Raises:
        ValueError: If any required column contains a missing value,
            naming which column(s).
    """
    missing_value_columns = [col for col in FEATURE_COLUMNS if df[col].isna().any()]

    if missing_value_columns:
        raise ValueError(f"Missing value(s) found in required column(s): {missing_value_columns}")


def validate_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Verify (and coerce) that numeric feature columns hold numeric values.

    Values are coerced via `pd.to_numeric` so common real-world inputs
    such as `age: "24"` (a numeric value serialized as a string, e.g.
    from a web form) are accepted; a value that cannot be interpreted
    as numeric at all raises an error rather than being silently
    dropped.

    Args:
        df: The single-row input DataFrame to validate.

    Returns:
        A new DataFrame with `NUMERIC_COLUMNS` coerced to numeric
        dtype.

    Raises:
        TypeError: If any value in a numeric column cannot be
            interpreted as a number.
    """
    result = df.copy()
    invalid_columns = []

    for column in NUMERIC_COLUMNS:
        coerced = pd.to_numeric(result[column], errors="coerce")
        if coerced.isna().any() and not result[column].isna().any():
            invalid_columns.append(column)
        result[column] = coerced

    if invalid_columns:
        raise TypeError(f"Non-numeric value(s) found in numeric column(s): {invalid_columns}")

    return result


def validate_categorical_columns(df: pd.DataFrame) -> None:
    """Verify that categorical feature columns hold string values.

    Args:
        df: The single-row input DataFrame to validate.

    Raises:
        TypeError: If any categorical column contains a non-string
            value, naming which column(s).
    """
    invalid_columns = [
        column for column in CATEGORICAL_COLUMNS if not df[column].map(lambda value: isinstance(value, str)).all()
    ]

    if invalid_columns:
        raise TypeError(f"Non-string value(s) found in categorical column(s): {invalid_columns}")


def validate_single_row(df: pd.DataFrame) -> None:
    """Verify that exactly one investor record was provided.

    This module returns a single dictionary (per the required output
    contract), so batch prediction over multiple rows is out of
    scope -- a multi-row DataFrame is rejected with a clear error
    rather than silently predicting only the first row.

    Args:
        df: The input DataFrame to validate.

    Raises:
        ValueError: If `df` does not contain exactly one row.
    """
    if len(df) != 1:
        raise ValueError(
            f"predict_investor_risk() expects exactly one investor record, got {len(df)}. "
            "Batch prediction is not supported by this function."
        )


# ----------------------------------------------------------------------------
# 5. Helper Functions
# ----------------------------------------------------------------------------
def convert_input_to_dataframe(user_input: Union[dict, pd.DataFrame]) -> pd.DataFrame:
    """Normalize a dict or DataFrame input into a DataFrame.

    Args:
        user_input: A single investor's raw survey answers, as either
            a dict (one investor) or a pandas DataFrame.

    Returns:
        A DataFrame representation of `user_input`.

    Raises:
        TypeError: If `user_input` is neither a dict nor a DataFrame.
    """
    if isinstance(user_input, dict):
        return pd.DataFrame([user_input])

    if isinstance(user_input, pd.DataFrame):
        return user_input.copy()

    raise TypeError(f"user_input must be a dict or pandas DataFrame, got {type(user_input).__name__}.")


def compute_confidence(probabilities: np.ndarray, predicted_class_index: int) -> float:
    """Extract the model's confidence in its predicted class.

    Args:
        probabilities: The row of class probabilities from
            `model.predict_proba()` for this investor.
        predicted_class_index: The encoded class index returned by
            `model.predict()` for this investor.

    Returns:
        The probability the model assigned to the predicted class,
        rounded to 4 decimal places.
    """
    return round(float(probabilities[predicted_class_index]), 4)


# ----------------------------------------------------------------------------
# 6. Model Loading
# ----------------------------------------------------------------------------
def load_model() -> RandomForestClassifier:
    """Load the already-trained classifier from disk. Does not fit anything.

    Returns:
        The loaded `RandomForestClassifier`.

    Raises:
        RuntimeError: If the file exists but could not be
            deserialized.
    """
    try:
        model = joblib.load(MODEL_FILEPATH)
    except Exception as exc:
        raise RuntimeError(f"Failed to load model from {MODEL_FILEPATH}: {exc}") from exc

    logger.info("Model loaded from %s", MODEL_FILEPATH)
    return model


def load_ordinal_encoder() -> OrdinalEncoder:
    """Load the already-fitted feature OrdinalEncoder from disk.

    Returns:
        The loaded `OrdinalEncoder`.

    Raises:
        RuntimeError: If the file exists but could not be
            deserialized.
    """
    try:
        ordinal_encoder = joblib.load(ORDINAL_ENCODER_FILEPATH)
    except Exception as exc:
        raise RuntimeError(f"Failed to load ordinal encoder from {ORDINAL_ENCODER_FILEPATH}: {exc}") from exc

    logger.info("Ordinal encoder loaded from %s", ORDINAL_ENCODER_FILEPATH)
    return ordinal_encoder


def load_label_encoder() -> LabelEncoder:
    """Load the already-fitted target LabelEncoder from disk.

    Returns:
        The loaded `LabelEncoder`.

    Raises:
        RuntimeError: If the file exists but could not be
            deserialized.
    """
    try:
        label_encoder = joblib.load(LABEL_ENCODER_FILEPATH)
    except Exception as exc:
        raise RuntimeError(f"Failed to load label encoder from {LABEL_ENCODER_FILEPATH}: {exc}") from exc

    logger.info("Label encoder loaded from %s | Classes: %s", LABEL_ENCODER_FILEPATH, list(label_encoder.classes_))
    return label_encoder


# ----------------------------------------------------------------------------
# 7. Input Validation
# ----------------------------------------------------------------------------
def validate_prediction_input(df: pd.DataFrame) -> pd.DataFrame:
    """Run every validation check required before prediction.

    Orchestrates, in order: single-row check, required/forbidden/
    unexpected column checks, missing-value check, numeric coercion,
    and categorical type check.

    Args:
        df: The raw input DataFrame, as normalized by
            `convert_input_to_dataframe`.

    Returns:
        A new DataFrame with numeric columns coerced, ready for
        feature engineering / preprocessing.

    Raises:
        ValueError: If the row count, required columns, forbidden
            columns, or missing values checks fail.
        TypeError: If a numeric or categorical column holds an
            invalid value type.
    """
    validate_single_row(df)
    validate_required_columns(df)
    validate_no_missing_values(df)
    validated_df = validate_numeric_columns(df)
    validate_categorical_columns(validated_df)

    logger.info("Input validated successfully.")
    return validated_df


# ----------------------------------------------------------------------------
# 8. Feature Engineering
# ----------------------------------------------------------------------------
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Arrange validated input into the exact feature set used at training time.

    The model was trained on the 24 raw survey features only -- none
    of the composite engineered columns (total_investment_score,
    age_group, etc.) are part of the training feature set, and all of
    them are explicitly forbidden as input to this module (see
    `FORBIDDEN_COLUMNS`). There is therefore no genuine feature
    engineering left to perform at inference time; this function's
    only job is to select and order columns to `FEATURE_COLUMNS`,
    kept as its own step so the pipeline shape mirrors the rest of
    this project and so any future legitimate derived feature has an
    obvious place to live.

    Args:
        df: The validated input DataFrame.

    Returns:
        A new DataFrame containing exactly `FEATURE_COLUMNS`, in that
        order.
    """
    return df[FEATURE_COLUMNS].copy()


# ----------------------------------------------------------------------------
# 9. Preprocessing
# ----------------------------------------------------------------------------
def encode_categorical_features(df: pd.DataFrame, ordinal_encoder: OrdinalEncoder) -> pd.DataFrame:
    """Ordinal-encode categorical columns using the already-fitted encoder.

    Only `.transform` is called -- the encoder is never fit here. The
    set of columns to encode is taken from the encoder's own
    `feature_names_in_` when available (the authoritative record of
    what it was actually fit on), falling back to `CATEGORICAL_COLUMNS`
    only if that attribute is absent (e.g. an older scikit-learn
    artifact).

    Args:
        df: The engineered feature DataFrame (see `engineer_features`).
        ordinal_encoder: The already-fitted `OrdinalEncoder`.

    Returns:
        A new DataFrame with categorical columns replaced by their
        ordinal-encoded values; numeric columns are left unchanged.
    """
    result = df.copy()
    categorical_columns = list(getattr(ordinal_encoder, "feature_names_in_", CATEGORICAL_COLUMNS))

    result[categorical_columns] = ordinal_encoder.transform(result[categorical_columns])

    logger.info("Categorical features encoded: %s", categorical_columns)
    return result


def align_feature_order(df: pd.DataFrame, model: RandomForestClassifier) -> pd.DataFrame:
    """Reorder columns to exactly match what the model was trained on.

    Uses the model's own `feature_names_in_` when available (the
    authoritative record of the training column order), falling back
    to `FEATURE_COLUMNS` only if that attribute is absent.

    Args:
        df: The encoded feature DataFrame.
        model: The already-fitted classifier.

    Returns:
        A new DataFrame with columns reordered to match training.
    """
    expected_order = list(getattr(model, "feature_names_in_", FEATURE_COLUMNS))
    return df[expected_order]

def preprocess_investor_input(
    user_input: Union[dict, pd.DataFrame],
    model: RandomForestClassifier,
    ordinal_encoder: OrdinalEncoder,
) -> pd.DataFrame:
    """
    Convert raw investor questionnaire input into the fully preprocessed
    feature matrix expected by the trained model.

    This function centralizes the preprocessing pipeline so it can be reused
    by both prediction and explainability modules (SHAP/LIME).

    Parameters
    ----------
    user_input : dict | pd.DataFrame
        Raw investor questionnaire responses.

    model : RandomForestClassifier
        Trained classifier.

    ordinal_encoder : OrdinalEncoder
        Fitted ordinal encoder.

    Returns
    -------
    pd.DataFrame
        Fully preprocessed feature matrix ready for inference.
    """

    raw_df = convert_input_to_dataframe(user_input)

    validated_df = validate_prediction_input(raw_df)

    engineered_df = engineer_features(validated_df)

    encoded_df = encode_categorical_features(
        engineered_df,
        ordinal_encoder
    )

    aligned_df = align_feature_order(
        encoded_df,
        model
    )

    return aligned_df
# ----------------------------------------------------------------------------
# 10. Prediction
# ----------------------------------------------------------------------------
def predict_risk_class(model: RandomForestClassifier, X: pd.DataFrame) -> tuple:
    """Generate a risk class prediction and its class probabilities.

    Args:
        model: The already-fitted classifier.
        X: The fully preprocessed, single-row feature matrix.

    Returns:
        A tuple of (predicted_class_index, probabilities), where
        `probabilities` is the row of class probabilities for this
        investor.

    Raises:
        RuntimeError: If prediction fails for any reason.
    """
    try:
        predicted_class_index = int(model.predict(X)[0])
        probabilities = model.predict_proba(X)[0]
    except Exception as exc:
        raise RuntimeError(f"Prediction failed: {exc}") from exc

    logger.info("Prediction completed.")
    return predicted_class_index, probabilities


# ----------------------------------------------------------------------------
# 11. Output Formatting
# ----------------------------------------------------------------------------
def format_prediction_output(
    predicted_class_index: int,
    probabilities: np.ndarray,
    label_encoder: LabelEncoder,
) -> dict:
    """Build the final result dictionary returned to the caller.

    Args:
        predicted_class_index: The encoded class index from
            `predict_risk_class`.
        probabilities: The row of class probabilities from
            `predict_risk_class`.
        label_encoder: The already-fitted `LabelEncoder`, used only to
            `.inverse_transform` (never fit) the predicted index back
            to a human-readable risk level.

    Returns:
        A dict of the form `{"risk_level": str, "confidence": float}`.
    """
    risk_level = label_encoder.inverse_transform([predicted_class_index])[0]
    confidence = compute_confidence(probabilities, predicted_class_index)

    logger.info("Confidence computed: %.4f", confidence)

    return {"risk_level": str(risk_level), "confidence": confidence}


# ----------------------------------------------------------------------------
# 12. Main function
# ----------------------------------------------------------------------------
def predict_investor_risk(user_input: Union[dict, pd.DataFrame]) -> dict:
    """Predict an investor's risk level from their raw survey answers.

    This is the single public entry point a backend service should
    call. It loads the trained model and fitted encoders (never
    fitting anything new), validates the input, encodes it exactly as
    it was encoded at training time, and returns a plain dictionary.

    Args:
        user_input: A single investor's raw survey answers, as either
            a dict (matching `FEATURE_COLUMNS`) or a one-row pandas
            DataFrame.

    Returns:
        A dict of the form `{"risk_level": str, "confidence": float}`.

    Raises:
        FileNotFoundError: If the model or either encoder file is
            missing.
        TypeError: If `user_input` is an unsupported type, or if a
            numeric/categorical column holds an invalid value type.
        ValueError: If required columns are missing, forbidden or
            unexpected columns are present, a value is missing, or
            more than one record is provided.
        RuntimeError: If an artifact fails to load or prediction
            fails.
    """
    validate_artifact_files_exist()

    model = load_model()
    ordinal_encoder = load_ordinal_encoder()
    label_encoder = load_label_encoder()

    aligned_df = preprocess_investor_input(
    user_input=user_input,
    model=model,
    ordinal_encoder=ordinal_encoder,
)

    predicted_class_index, probabilities = predict_risk_class(model, aligned_df)

    return format_prediction_output(predicted_class_index, probabilities, label_encoder)


# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    setup_logger()

    example_input = {
        "gender": "Female",
        "age": 24,
        "investment_avenues": "Yes",
        "mutual_funds": 1,
        "equity_market": 2,
        "debentures": 5,
        "government_bonds": 3,
        "fixed_deposits": 7,
        "ppf": 6,
        "gold": 4,
        "stock_market": "Yes",
        "factor": "Returns",
        "objective": "Growth",
        "purpose": "Wealth Creation",
        "duration": "1-3 years",
        "invest_monitor": "Monthly",
        "expect": "20%-30%",
        "avenue": "Mutual Fund",
        "what_are_your_savings_objectives": "Retirement Plan",
        "reason_equity": "Capital Appreciation",
        "reason_mutual": "Better Returns",
        "reason_bonds": "Safe Investment",
        "reason_fd": "Fixed Returns",
        "source": "Internet",
    }

    print(predict_investor_risk(example_input))