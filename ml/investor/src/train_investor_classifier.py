"""Train a Random Forest classifier to predict investor Investor_Risk_Level.

This module is the model-training stage of the Investor Profiling
pipeline (a separate pipeline from the Stock Risk Prediction pipeline,
sharing the same architecture and coding conventions). Its sole
responsibility is to train and evaluate a Random Forest classifier
that predicts `Investor_Risk_Level` from the engineered investor
features in `ml/investor/data/processed/investor_labeled_training_dataset.csv`,
and persist the trained model, fitted encoders, held-out data splits,
evaluation report, and figures.

IMPORTANT -- TARGET LEAKAGE:
`investor_risk_score` (and its pre-dampening variant
`investor_risk_score_raw`, plus `signal_agreement` and
`advisor_confidence`) are all values `generate_risk_labels.py` derives
directly from the same rule contributions used to compute the target
label. `total_investment_score`, `preferred_safe_assets`,
`preferred_market_assets`, `investment_diversification_score`, and
`age_group` are themselves direct inputs to that scoring formula.
Training on any of these would let the model reconstruct the labeling
rule instead of learning from genuine investor behaviour, so all of
them are excluded from the feature matrix via `LEAKAGE_COLUMNS`.

METHODOLOGY -- HYPERPARAMETER TUNING:
`train_model` performs a `GridSearchCV` over a modest parameter grid
using `StratifiedKFold` cross-validation rather than fitting a single
hardcoded configuration. Out-of-bag score, mean cross-validation
accuracy, and separate train/test accuracy are all reported so
overfitting can be detected directly rather than assumed.

Typical usage:
    python -m src.train_investor_classifier
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------
import json
import logging
from pathlib import Path
from typing import Final, Optional

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)

# ----------------------------------------------------------------------------
# Configuration Constants
# ----------------------------------------------------------------------------
# ml/investor/src/train_investor_classifier.py -> parent (src) -> parent (investor)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Input file produced by generate_risk_labels.py.
INPUT_FILEPATH: Final[Path] = BASE_DIR / "data" / "processed" / "investor_labeled_training_dataset.csv"

#: Directory where the trained model and fitted encoders are saved.
MODELS_DIR: Final[Path] = BASE_DIR / "models"

#: Output path for the trained classifier.
MODEL_FILEPATH: Final[Path] = MODELS_DIR / "investor_risk_classifier.pkl"

#: Output path for the fitted target LabelEncoder.
LABEL_ENCODER_FILEPATH: Final[Path] = MODELS_DIR / "label_encoder.pkl"

#: Output path for the fitted feature OrdinalEncoder.
ORDINAL_ENCODER_FILEPATH: Final[Path] = MODELS_DIR / "ordinal_encoder.pkl"

#: Directory where text reports are saved.
REPORTS_DIR: Final[Path] = BASE_DIR / "reports"

#: Output path for the classification report.
CLASSIFICATION_REPORT_FILEPATH: Final[Path] = REPORTS_DIR / "classification_report.txt"

#: Output path for the best hyperparameters found by GridSearchCV.
BEST_PARAMS_FILEPATH: Final[Path] = REPORTS_DIR / "best_params.json"

#: Directory where evaluation figures are saved.
FIGURES_DIR: Final[Path] = REPORTS_DIR / "figures"

#: Filename for the confusion matrix figure.
CONFUSION_MATRIX_FILENAME: Final[str] = "confusion_matrix.png"

#: Filename for the feature importance figure.
FEATURE_IMPORTANCE_FILENAME: Final[str] = "feature_importance.png"

#: Directory where the held-out train/test splits are saved, so a
#: separate evaluation module can load them without retraining or
#: risking a different split.
PROCESSED_DATA_DIR: Final[Path] = BASE_DIR / "data" / "processed"

#: Output path for the encoded training split (features + original
#: string target), for reuse by a separate evaluation module.
TRAIN_SPLIT_FILEPATH: Final[Path] = PROCESSED_DATA_DIR / "investor_train_split.csv"

#: Output path for the encoded test split (features + original string
#: target), for reuse by a separate evaluation module.
TEST_SPLIT_FILEPATH: Final[Path] = PROCESSED_DATA_DIR / "investor_test_split.csv"

#: Target column to predict.
TARGET_COLUMN: Final[str] = "Investor_Risk_Level"

#: Columns excluded from the feature matrix because they would leak
#: the target, either directly (investor_risk_score and its
#: variants -- the exact values used to derive the label) or
#: functionally (the composite features that are themselves direct
#: inputs to the scoring formula that produced the label).
LEAKAGE_COLUMNS: Final[list] = [
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

#: Fraction of data held out for the test set.
TEST_SIZE: Final[float] = 0.2

#: Random seed used for the train/test split and the model.
RANDOM_STATE: Final[int] = 42

#: Placeholder used to fill missing categorical values before ordinal
#: encoding, since OrdinalEncoder cannot encode NaN directly.
MISSING_CATEGORY_PLACEHOLDER: Final[str] = "Missing"

#: Number of cross-validation folds used during hyperparameter search.
CV_FOLDS: Final[int] = 5

#: Hyperparameter grid searched via GridSearchCV. Kept intentionally
#: modest (3 values per parameter) so the search stays fast and the
#: result stays easy to reason about, rather than an exhaustive sweep.
PARAM_GRID: Final[dict] = {
    "n_estimators": [100, 200, 300],
    "max_depth": [5, 10, None],
    "min_samples_leaf": [1, 5, 10],
    "min_samples_split": [2, 10, 20],
}

#: If (train_accuracy - test_accuracy) exceeds this, the model is
#: flagged as showing signs of overfitting.
OVERFITTING_GAP_THRESHOLD: Final[float] = 0.10

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
def _identify_categorical_columns(df: pd.DataFrame) -> list:
    """Identify string-typed (categorical) columns in a feature matrix.

    Uses `pd.api.types.is_string_dtype` rather than checking for
    `object` dtype specifically, since pandas may represent text
    columns as either legacy `object` dtype or the newer `StringDtype`
    depending on version/configuration -- checking only `object` would
    silently miss categorical columns on newer pandas versions.

    Args:
        df: The feature matrix to inspect.

    Returns:
        A list of column names identified as categorical.
    """
    return [col for col in df.columns if pd.api.types.is_string_dtype(df[col])]


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
    """Run all validation checks required before training.

    Checks that the target column exists, the dataframe is non-empty,
    and that no duplicate rows or duplicate column names exist.

    Args:
        df: The loaded dataset.

    Returns:
        True only if every individual validation check passes, False
        if any check fails.
    """
    checks = {
        "target column exists": TARGET_COLUMN in df.columns,
        "dataframe not empty": not df.empty,
        "no duplicate rows": not df.duplicated().any(),
        "no duplicate columns": not df.columns.duplicated().any(),
    }

    for check_name, passed in checks.items():
        logger.info("Validation check '%s': %s", check_name, "PASSED" if passed else "FAILED")

    return all(checks.values())


# ----------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------
def load_dataset(filepath: Path) -> Optional[pd.DataFrame]:
    """Load the labeled investor training dataset from a CSV file.

    Args:
        filepath: Path to `investor_labeled_training_dataset.csv`.

    Returns:
        The loaded DataFrame, or None if the file could not be read.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception:
        logger.error("Failed to load dataset: %s", filepath, exc_info=True)
        return None

    logger.info("Dataset loaded from %s | Shape: %s", filepath, df.shape)
    return df


# ----------------------------------------------------------------------------
# Preprocessing
# ----------------------------------------------------------------------------
def select_features(df: pd.DataFrame) -> tuple:
    """Separate the dataset into a feature matrix X and target vector y.

    Excludes `TARGET_COLUMN` and all `LEAKAGE_COLUMNS` (the score
    columns that determined the target, plus the composite features
    that are themselves direct inputs to that scoring formula) from
    the feature set.

    Args:
        df: The validated dataset.

    Returns:
        A tuple of (X, y) where X is a DataFrame of feature columns
        and y is a Series of raw (unencoded) Investor_Risk_Level
        values.
    """
    excluded_columns = [TARGET_COLUMN] + LEAKAGE_COLUMNS
    feature_columns = [col for col in df.columns if col not in excluded_columns]

    X = df[feature_columns].copy()
    y = df[TARGET_COLUMN].copy()

    logger.info("Excluded from features (target + leakage): %s", excluded_columns)
    logger.info("Features used (%d): %s", len(feature_columns), feature_columns)
    logger.info("Target distribution:\n%s", y.value_counts().to_string())

    return X, y


def encode_target(y: pd.Series) -> tuple:
    """Encode string Investor_Risk_Level values into integer labels.

    Args:
        y: A Series of raw (unencoded) Investor_Risk_Level values.

    Returns:
        A tuple of (y_encoded, label_encoder) where y_encoded is a
        numpy array of integer-encoded labels and label_encoder is
        the fitted `LabelEncoder`.
    """
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    logger.info("Encoded classes: %s", dict(enumerate(label_encoder.classes_)))
    return y_encoded, label_encoder


def split_dataset(X: pd.DataFrame, y_encoded: np.ndarray) -> tuple:
    """Split features and encoded target into train and test sets.

    Uses an 80/20 split, stratified by the encoded target so class
    proportions are preserved in both splits.

    Args:
        X: The feature matrix (not yet ordinal-encoded).
        y_encoded: The integer-encoded target vector.

    Returns:
        A tuple of (X_train, X_test, y_train, y_test).
    """
    return train_test_split(
        X,
        y_encoded,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y_encoded,
    )


def encode_categorical_features(X_train: pd.DataFrame, X_test: pd.DataFrame) -> tuple:
    """Ordinal-encode categorical feature columns, fit on train only.

    The `OrdinalEncoder` is fit on `X_train` only and then used to
    transform both `X_train` and `X_test`. Fitting on train only (not
    the full dataset before splitting) avoids leaking test-set
    category information into training, and `handle_unknown=
    "use_encoded_value"` with `unknown_value=-1` ensures a category
    that appears only in the test set does not raise an error.
    Missing values in categorical columns are filled with
    `MISSING_CATEGORY_PLACEHOLDER` first, since `OrdinalEncoder`
    cannot encode NaN directly.

    Args:
        X_train: Training feature matrix.
        X_test: Test feature matrix.

    Returns:
        A tuple of (X_train_encoded, X_test_encoded, ordinal_encoder).
        Numeric columns are left unchanged; categorical columns are
        replaced with their ordinal-encoded integer values.
    """
    X_train_encoded = X_train.copy()
    X_test_encoded = X_test.copy()

    categorical_columns = _identify_categorical_columns(X_train_encoded)

    if not categorical_columns:
        logger.info("No categorical feature columns found; skipping ordinal encoding.")
        return X_train_encoded, X_test_encoded, None

    for column in categorical_columns:
        X_train_encoded[column] = X_train_encoded[column].fillna(MISSING_CATEGORY_PLACEHOLDER)
        X_test_encoded[column] = X_test_encoded[column].fillna(MISSING_CATEGORY_PLACEHOLDER)

    ordinal_encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    X_train_encoded[categorical_columns] = ordinal_encoder.fit_transform(X_train_encoded[categorical_columns])
    X_test_encoded[categorical_columns] = ordinal_encoder.transform(X_test_encoded[categorical_columns])

    logger.info("Ordinal-encoded %d categorical column(s): %s", len(categorical_columns), categorical_columns)

    return X_train_encoded, X_test_encoded, ordinal_encoder


# ----------------------------------------------------------------------------
# Model Training
# ----------------------------------------------------------------------------
def train_model(X_train: pd.DataFrame, y_train: np.ndarray) -> Optional[dict]:
    """Tune and train a Random Forest classifier via GridSearchCV.

    Searches `PARAM_GRID` using `StratifiedKFold` cross-validation
    (`CV_FOLDS` folds) rather than fitting one hardcoded
    configuration. The base estimator enables `oob_score=True` /
    `bootstrap=True` so an out-of-bag accuracy estimate is available
    on the final fitted model without any extra held-out data.

    Args:
        X_train: Training feature matrix (ordinal-encoded).
        y_train: Training target vector (encoded).

    Returns:
        A dict with keys `model` (the best fitted
        `RandomForestClassifier`), `best_params`, and
        `cv_mean_accuracy`, or None if training failed.
    """
    missing_count = int(X_train.isna().sum().sum())
    if missing_count > 0:
        logger.warning("X_train contains %d missing value(s) prior to training.", missing_count)

    base_model = RandomForestClassifier(random_state=RANDOM_STATE, oob_score=True, bootstrap=True)
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)

    logger.info(
        "Training started: GridSearchCV(RandomForestClassifier, cv=StratifiedKFold(%d), grid=%s)",
        CV_FOLDS,
        PARAM_GRID,
    )

    try:
        search = GridSearchCV(
            estimator=base_model,
            param_grid=PARAM_GRID,
            cv=cv,
            scoring="accuracy",
            n_jobs=-1,
        )
        search.fit(X_train, y_train)
    except Exception:
        logger.error("Model training failed.", exc_info=True)
        return None

    logger.info("Training completed.")
    logger.info("Best hyperparameters: %s", search.best_params_)
    logger.info("Mean cross-validation accuracy (best params): %.4f", search.best_score_)

    return {
        "model": search.best_estimator_,
        "best_params": search.best_params_,
        "cv_mean_accuracy": float(search.best_score_),
    }


def compute_oob_score(model: RandomForestClassifier) -> Optional[float]:
    """Retrieve the out-of-bag accuracy estimate from a fitted model.

    Args:
        model: The fitted classifier (must have been trained with
            `oob_score=True, bootstrap=True`).

    Returns:
        The OOB score, or None if unavailable.
    """
    oob_score = getattr(model, "oob_score_", None)

    if oob_score is None:
        logger.warning("OOB score not available on the fitted model.")
    else:
        logger.info("Out-of-bag (OOB) accuracy: %.4f", oob_score)

    return oob_score


def compute_train_test_accuracy(
    model: RandomForestClassifier,
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
) -> dict:
    """Compute training accuracy and testing accuracy separately.

    Args:
        model: The fitted classifier.
        X_train: Training feature matrix.
        y_train: Training target vector (encoded).
        X_test: Test feature matrix.
        y_test: Test target vector (encoded).

    Returns:
        A dict with `train_accuracy` and `test_accuracy`.
    """
    train_accuracy = accuracy_score(y_train, model.predict(X_train))
    test_accuracy = accuracy_score(y_test, model.predict(X_test))

    logger.info("Training accuracy: %.4f", train_accuracy)
    logger.info("Testing accuracy: %.4f", test_accuracy)

    return {"train_accuracy": float(train_accuracy), "test_accuracy": float(test_accuracy)}


def detect_overfitting(train_accuracy: float, test_accuracy: float) -> dict:
    """Flag possible overfitting by comparing train and test accuracy.

    Args:
        train_accuracy: Accuracy on the training set.
        test_accuracy: Accuracy on the held-out test set.

    Returns:
        A dict with `gap` (train minus test accuracy) and
        `overfitting_detected` (True if `gap` exceeds
        `OVERFITTING_GAP_THRESHOLD`).
    """
    gap = train_accuracy - test_accuracy
    overfitting_detected = gap > OVERFITTING_GAP_THRESHOLD

    if overfitting_detected:
        logger.warning(
            "Possible overfitting detected: train accuracy exceeds test accuracy by %.4f "
            "(threshold: %.4f).",
            gap,
            OVERFITTING_GAP_THRESHOLD,
        )
    else:
        logger.info(
            "No strong overfitting signal: train/test accuracy gap is %.4f (threshold: %.4f).",
            gap,
            OVERFITTING_GAP_THRESHOLD,
        )

    return {"gap": float(gap), "overfitting_detected": bool(overfitting_detected)}


# ----------------------------------------------------------------------------
# Evaluation
# ----------------------------------------------------------------------------
def evaluate_model(
    model: RandomForestClassifier,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    label_encoder: LabelEncoder,
) -> dict:
    """Evaluate a trained model on the held-out test set.

    Computes accuracy, precision, recall, F1 score (all macro-
    averaged to treat each risk class equally), a full classification
    report, and a confusion matrix.

    Args:
        model: The fitted classifier.
        X_test: Test feature matrix (ordinal-encoded).
        y_test: Test target vector (encoded).
        label_encoder: The fitted `LabelEncoder`, used to recover
            human-readable class names for the report.

    Returns:
        A dict containing `accuracy`, `precision`, `recall`, `f1`,
        `report_text`, `confusion_matrix`, `y_pred`, and `class_names`.
    """
    y_pred = model.predict(X_test)
    class_names = label_encoder.classes_

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, average="macro", zero_division=0),
        "recall": recall_score(y_test, y_pred, average="macro", zero_division=0),
        "f1": f1_score(y_test, y_pred, average="macro", zero_division=0),
        "report_text": classification_report(y_test, y_pred, target_names=class_names, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, y_pred),
        "y_pred": y_pred,
        "class_names": class_names,
    }

    logger.info(
        "Evaluation metrics | Accuracy: %.4f | Precision: %.4f | Recall: %.4f | F1: %.4f",
        metrics["accuracy"],
        metrics["precision"],
        metrics["recall"],
        metrics["f1"],
    )
    logger.info("Classification report:\n%s", metrics["report_text"])

    return metrics


def compute_roc_auc(model: RandomForestClassifier, X_test: pd.DataFrame, y_test: np.ndarray) -> Optional[float]:
    """Compute macro-averaged one-vs-rest ROC-AUC for the multi-class problem.

    Args:
        model: The fitted classifier (must support `predict_proba`).
        X_test: Test feature matrix.
        y_test: Test target vector (encoded).

    Returns:
        The macro-averaged ROC-AUC score, or None if it could not be
        computed (e.g. the model lacks `predict_proba`, or a class is
        entirely absent from `y_test`).
    """
    if not hasattr(model, "predict_proba"):
        logger.warning("Model does not support predict_proba; skipping ROC-AUC.")
        return None

    try:
        y_proba = model.predict_proba(X_test)
        roc_auc = roc_auc_score(y_test, y_proba, multi_class="ovr", average="macro")
    except ValueError:
        logger.warning("ROC-AUC could not be computed (e.g. a class missing from y_test).", exc_info=True)
        return None

    logger.info("ROC-AUC (macro, one-vs-rest): %.4f", roc_auc)
    return float(roc_auc)


# ----------------------------------------------------------------------------
# Visualization
# ----------------------------------------------------------------------------
def plot_confusion_matrix(cm: np.ndarray, class_names: np.ndarray) -> Path:
    """Create and save a confusion matrix heatmap using matplotlib only.

    Args:
        cm: The confusion matrix array.
        class_names: Human-readable class names, in the order used by
            the confusion matrix rows/columns.

    Returns:
        The path the figure was saved to.
    """
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(cm, cmap="Blues")

    ax.set_xticks(range(len(class_names)))
    ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=45)
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Predicted Label")
    ax.set_ylabel("True Label")
    ax.set_title("Confusion Matrix")

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            text_color = "white" if cm[i, j] > cm.max() / 2 else "black"
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", color=text_color)

    fig.colorbar(im, ax=ax, label="Count")
    fig.tight_layout()

    filepath = FIGURES_DIR / CONFUSION_MATRIX_FILENAME
    fig.savefig(filepath)
    plt.close(fig)

    return filepath


def plot_feature_importance(model: RandomForestClassifier, feature_names: list) -> Path:
    """Create and save a descending-sorted feature importance bar chart.

    Args:
        model: The fitted classifier.
        feature_names: Names of the features, in the same order used
            during training.

    Returns:
        The path the figure was saved to.
    """
    importances = pd.Series(model.feature_importances_, index=feature_names).sort_values(ascending=False)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(importances.index[::-1], importances.values[::-1])
    ax.set_title("Feature Importance")
    ax.set_xlabel("Importance")
    ax.set_ylabel("Feature")
    ax.grid(True, axis="x")
    fig.tight_layout()

    filepath = FIGURES_DIR / FEATURE_IMPORTANCE_FILENAME
    fig.savefig(filepath)
    plt.close(fig)

    return filepath


# ----------------------------------------------------------------------------
# Save Functions
# ----------------------------------------------------------------------------
def save_model(model: RandomForestClassifier) -> Optional[Path]:
    """Persist the trained model using joblib.

    Args:
        model: The fitted classifier.

    Returns:
        The path the model was saved to, or None if saving failed.
    """
    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, MODEL_FILEPATH)
    except Exception:
        logger.error("Failed to save model to %s", MODEL_FILEPATH, exc_info=True)
        return None

    return MODEL_FILEPATH


def save_label_encoder(label_encoder: LabelEncoder) -> Optional[Path]:
    """Persist the fitted target LabelEncoder using joblib.

    Saved so a separate evaluation or inference module can decode
    predictions back to class names without refitting.

    Args:
        label_encoder: The fitted `LabelEncoder`.

    Returns:
        The path the encoder was saved to, or None if saving failed.
    """
    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(label_encoder, LABEL_ENCODER_FILEPATH)
    except Exception:
        logger.error("Failed to save label encoder to %s", LABEL_ENCODER_FILEPATH, exc_info=True)
        return None

    return LABEL_ENCODER_FILEPATH


def save_ordinal_encoder(ordinal_encoder: Optional[OrdinalEncoder]) -> Optional[Path]:
    """Persist the fitted feature OrdinalEncoder using joblib.

    Saved so a separate evaluation or inference module can encode new
    categorical data consistently without refitting.

    Args:
        ordinal_encoder: The fitted `OrdinalEncoder`, or None if there
            were no categorical columns to encode.

    Returns:
        The path the encoder was saved to, or None if there was
        nothing to save or saving failed.
    """
    if ordinal_encoder is None:
        logger.info("No ordinal encoder to save (no categorical columns were present).")
        return None

    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(ordinal_encoder, ORDINAL_ENCODER_FILEPATH)
    except Exception:
        logger.error("Failed to save ordinal encoder to %s", ORDINAL_ENCODER_FILEPATH, exc_info=True)
        return None

    return ORDINAL_ENCODER_FILEPATH


def save_best_params(best_params: dict, cv_mean_accuracy: float) -> Optional[Path]:
    """Persist the best hyperparameters found by GridSearchCV as JSON.

    Args:
        best_params: The `best_params_` dict from `GridSearchCV`.
        cv_mean_accuracy: The mean cross-validation accuracy achieved
            by those parameters.

    Returns:
        The path the JSON file was written to, or None if saving
        failed.
    """
    payload = {"best_params": best_params, "cv_mean_accuracy": cv_mean_accuracy}

    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        BEST_PARAMS_FILEPATH.write_text(json.dumps(payload, indent=2))
    except Exception:
        logger.error("Failed to save best parameters to %s", BEST_PARAMS_FILEPATH, exc_info=True)
        return None

    return BEST_PARAMS_FILEPATH


def save_train_test_split(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_test: pd.DataFrame,
    y_test: np.ndarray,
    label_encoder: LabelEncoder,
) -> tuple:
    """Persist the encoded train and test splits, with decoded labels.

    Saved so a separate evaluation module can load the exact held-out
    test set (and the matching train set, for overfitting comparison)
    without needing to reproduce the split.

    Args:
        X_train: Training feature matrix (ordinal-encoded).
        y_train: Training target vector (encoded).
        X_test: Test feature matrix (ordinal-encoded).
        y_test: Test target vector (encoded).
        label_encoder: The fitted `LabelEncoder`, used to write the
            original string labels alongside the encoded features.

    Returns:
        A tuple of (train_split_path, test_split_path), each either a
        `Path` or None if saving that split failed.
    """
    train_df = X_train.copy()
    train_df[TARGET_COLUMN] = label_encoder.inverse_transform(y_train)

    test_df = X_test.copy()
    test_df[TARGET_COLUMN] = label_encoder.inverse_transform(y_test)

    train_path: Optional[Path] = None
    test_path: Optional[Path] = None

    try:
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        train_df.to_csv(TRAIN_SPLIT_FILEPATH, index=False)
        train_path = TRAIN_SPLIT_FILEPATH
    except Exception:
        logger.error("Failed to save training split to %s", TRAIN_SPLIT_FILEPATH, exc_info=True)

    try:
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        test_df.to_csv(TEST_SPLIT_FILEPATH, index=False)
        test_path = TEST_SPLIT_FILEPATH
    except Exception:
        logger.error("Failed to save test split to %s", TEST_SPLIT_FILEPATH, exc_info=True)

    return train_path, test_path


def save_report(metrics: dict, training_summary: dict) -> Optional[Path]:
    """Write a plain-text evaluation report to disk.

    Args:
        metrics: The dict returned by `evaluate_model`.
        training_summary: A dict combining `best_params`,
            `cv_mean_accuracy`, `oob_score`, `train_accuracy`,
            `test_accuracy`, `overfitting_detected`, `gap`, and
            `roc_auc`.

    Returns:
        The path the report was saved to, or None if saving failed.
    """
    lines = [
        "Investor Risk Classifier -- Evaluation Report",
        "=" * 50,
        f"Best hyperparameters: {training_summary['best_params']}",
        f"Mean CV accuracy:  {training_summary['cv_mean_accuracy']:.4f}",
        f"OOB accuracy:      {training_summary['oob_score']:.4f}"
        if training_summary["oob_score"] is not None
        else "OOB accuracy:      N/A",
        f"Train accuracy:    {training_summary['train_accuracy']:.4f}",
        f"Test accuracy:     {training_summary['test_accuracy']:.4f}",
        f"Train-test gap:    {training_summary['gap']:.4f}",
        f"Overfitting detected: {training_summary['overfitting_detected']}",
        f"ROC-AUC (macro, OVR): {training_summary['roc_auc']:.4f}"
        if training_summary["roc_auc"] is not None
        else "ROC-AUC (macro, OVR): N/A",
        "",
        f"Accuracy:  {metrics['accuracy']:.4f}",
        f"Precision (macro): {metrics['precision']:.4f}",
        f"Recall (macro):    {metrics['recall']:.4f}",
        f"F1 Score (macro):  {metrics['f1']:.4f}",
        "",
        "Classification Report",
        "-" * 50,
        metrics["report_text"],
    ]

    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        CLASSIFICATION_REPORT_FILEPATH.write_text("\n".join(lines))
    except Exception:
        logger.error("Failed to save classification report to %s", CLASSIFICATION_REPORT_FILEPATH, exc_info=True)
        return None

    return CLASSIFICATION_REPORT_FILEPATH


# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------
def summarize_results(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    metrics: dict,
    training_summary: dict,
    model_path: Path,
    report_path: Path,
) -> None:
    """Print and log a final summary of the training run.

    Args:
        X_train: Training feature matrix.
        X_test: Test feature matrix.
        metrics: The dict returned by `evaluate_model`.
        training_summary: The combined tuning/overfitting summary dict
            (see `save_report`).
        model_path: The path the trained model was saved to.
        report_path: The path the classification report was saved to.
    """
    logger.info("===== Investor Risk Classifier Training Summary =====")
    logger.info("Train size: %d", len(X_train))
    logger.info("Test size: %d", len(X_test))
    logger.info("Best hyperparameters: %s", training_summary["best_params"])
    logger.info("Mean CV accuracy: %.4f", training_summary["cv_mean_accuracy"])
    logger.info("OOB accuracy: %s", training_summary["oob_score"])
    logger.info("Train accuracy: %.4f", training_summary["train_accuracy"])
    logger.info("Test accuracy: %.4f", training_summary["test_accuracy"])
    logger.info("Overfitting detected: %s", training_summary["overfitting_detected"])
    logger.info("Test-set accuracy (evaluate_model): %.4f", metrics["accuracy"])
    logger.info("Number of features: %d", X_train.shape[1])
    logger.info("Model saved to: %s", model_path)
    logger.info("Report saved to: %s", report_path)
    logger.info("=======================================================")

    print("=" * 60)
    print("Investor Risk Classifier -- Final Summary")
    print("=" * 60)
    print(f"Train size          : {len(X_train)}")
    print(f"Test size           : {len(X_test)}")
    print(f"Best hyperparameters: {training_summary['best_params']}")
    print(f"Mean CV accuracy    : {training_summary['cv_mean_accuracy']:.4f}")
    oob_display = f"{training_summary['oob_score']:.4f}" if training_summary["oob_score"] is not None else "N/A"
    print(f"OOB accuracy        : {oob_display}")
    print(f"Train accuracy      : {training_summary['train_accuracy']:.4f}")
    print(f"Test accuracy       : {training_summary['test_accuracy']:.4f}")
    print(f"Overfitting detected: {training_summary['overfitting_detected']}")
    print(f"Accuracy            : {metrics['accuracy']:.4f}")
    print(f"Number of features  : {X_train.shape[1]}")
    print(f"Model save path     : {model_path}")
    print(f"Report save path    : {report_path}")
    print("=" * 60)


# ----------------------------------------------------------------------------
# Main Function
# ----------------------------------------------------------------------------
def main() -> None:
    """Train, evaluate, and save the investor risk classifier.

    Orchestrates: validate input exists -> load -> validate dataset ->
    select features/target -> encode target -> split -> encode
    categorical features -> tune/train -> compute OOB/train/test
    accuracy -> detect overfitting -> evaluate on test set -> compute
    ROC-AUC -> plot -> save model/encoders/splits/params/report ->
    summarize. Aborts early if the input file is missing, the dataset
    fails validation, or training fails.
    """
    logger.info("Starting investor risk classifier training.")

    if not validate_input_file():
        logger.error("Aborting: required input file is missing.")
        return

    df = load_dataset(INPUT_FILEPATH)
    if df is None:
        logger.error("Aborting: dataset could not be loaded.")
        return

    if not validate_dataset(df):
        logger.error("Validation failed. Aborting training.")
        return

    X, y = select_features(df)
    y_encoded, label_encoder = encode_target(y)

    X_train, X_test, y_train, y_test = split_dataset(X, y_encoded)
    logger.info("Train shape: %s | Test shape: %s", X_train.shape, X_test.shape)

    X_train_encoded, X_test_encoded, ordinal_encoder = encode_categorical_features(X_train, X_test)

    training_result = train_model(X_train_encoded, y_train)
    if training_result is None:
        logger.error("Aborting: model training failed.")
        return

    model = training_result["model"]

    oob_score = compute_oob_score(model)
    accuracy_summary = compute_train_test_accuracy(model, X_train_encoded, y_train, X_test_encoded, y_test)
    overfitting_summary = detect_overfitting(accuracy_summary["train_accuracy"], accuracy_summary["test_accuracy"])

    metrics = evaluate_model(model, X_test_encoded, y_test, label_encoder)
    roc_auc = compute_roc_auc(model, X_test_encoded, y_test)

    training_summary = {
        "best_params": training_result["best_params"],
        "cv_mean_accuracy": training_result["cv_mean_accuracy"],
        "oob_score": oob_score,
        "train_accuracy": accuracy_summary["train_accuracy"],
        "test_accuracy": accuracy_summary["test_accuracy"],
        "gap": overfitting_summary["gap"],
        "overfitting_detected": overfitting_summary["overfitting_detected"],
        "roc_auc": roc_auc,
    }

    plot_confusion_matrix(metrics["confusion_matrix"], metrics["class_names"])
    plot_feature_importance(model, list(X_train_encoded.columns))

    model_path = save_model(model)
    label_encoder_path = save_label_encoder(label_encoder)
    ordinal_encoder_path = save_ordinal_encoder(ordinal_encoder)
    best_params_path = save_best_params(training_result["best_params"], training_result["cv_mean_accuracy"])
    train_split_path, test_split_path = save_train_test_split(
        X_train_encoded, y_train, X_test_encoded, y_test, label_encoder
    )
    report_path = save_report(metrics, training_summary)

    if model_path is None or label_encoder_path is None or report_path is None:
        logger.error("One or more critical output files failed to save.")
        return

    logger.info(
        "Additional artifacts saved | Ordinal encoder: %s | Best params: %s | Train split: %s | Test split: %s",
        ordinal_encoder_path,
        best_params_path,
        train_split_path,
        test_split_path,
    )

    summarize_results(X_train_encoded, X_test_encoded, metrics, training_summary, model_path, report_path)
    logger.info("Investor risk classifier training pipeline complete.")


# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    setup_logger()
    main()