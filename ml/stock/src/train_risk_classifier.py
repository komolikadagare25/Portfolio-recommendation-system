"""Train a Random Forest classifier to predict stock Risk_Level.

This module is the first machine-learning training stage of the
Explainable AI-Based Portfolio Recommendation System pipeline. Its
sole responsibility is to train and evaluate a Random Forest
classifier that predicts `Risk_Level` from the engineered numerical
features in `ml/data/processed/labeled_training_dataset.csv`, and
persist the trained model, label encoder, classification report, and
evaluation figures.

This is Version 1 of the model and is intentionally kept simple.

This module MUST NOT:
    * Perform feature engineering or modify the input dataset.
    * Rebalance classes.
    * Perform extensive hyperparameter tuning or GridSearchCV.
    * Implement SHAP or LIME explanations.

Those responsibilities belong to other stages of the pipeline.

Typical usage:
    python -m src.train_risk_classifier
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------
import logging
from pathlib import Path
from typing import Final, Optional

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

# ----------------------------------------------------------------------------
# Configuration / Constants
# ----------------------------------------------------------------------------
# ml/src/train_risk_classifier.py -> parent (src) -> parent (ml)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Input file produced by generate_risk_labels.py.
INPUT_FILEPATH: Final[Path] = BASE_DIR / "data" / "processed" / "labeled_training_dataset.csv"

#: Directory where trained model artifacts are saved.
MODELS_DIR: Final[Path] = BASE_DIR / "models"

#: Output path for the trained classifier.
MODEL_FILEPATH: Final[Path] = MODELS_DIR / "risk_classifier.pkl"

#: Output path for the fitted label encoder.
ENCODER_FILEPATH: Final[Path] = MODELS_DIR / "label_encoder.pkl"

#: Directory where text reports are saved.
REPORTS_DIR: Final[Path] = BASE_DIR / "reports"

#: Output path for the classification report.
CLASSIFICATION_REPORT_FILEPATH: Final[Path] = REPORTS_DIR / "classification_report.txt"

#: Directory where evaluation figures are saved.
FIGURES_DIR: Final[Path] = REPORTS_DIR / "figures"

#: Filename for the confusion matrix figure.
CONFUSION_MATRIX_FILENAME: Final[str] = "confusion_matrix.png"

#: Filename for the feature importance figure.
FEATURE_IMPORTANCE_FILENAME: Final[str] = "feature_importance.png"

#: Target column to predict.
TARGET_COLUMN: Final[str] = "Risk_Level"

#: Identifier columns excluded from the feature set (not predictive features).
IDENTIFIER_COLUMNS: Final[list] = ["Stock", "Date"]

#: Columns that together uniquely identify a row.
ROW_IDENTIFIER_COLUMNS: Final[list] = ["Stock", "Date"]

#: Fraction of data held out for the test set.
TEST_SIZE: Final[float] = 0.2

#: Random seed used for the train/test split, model, and cross-validation.
RANDOM_STATE: Final[int] = 42

#: Number of folds for cross-validation.
CV_FOLDS: Final[int] = 5

#: Random Forest hyperparameters. Kept simple and reasonable; not tuned.
N_ESTIMATORS: Final[int] = 200
MAX_DEPTH: Final[Optional[int]] = 10

#: Logging verbosity for this module.
LOG_LEVEL: Final[int] = logging.INFO

# ----------------------------------------------------------------------------
# Logger
# ----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def setup_logger() -> None:
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
def validate_file_exists(filepath: Path) -> bool:
    """Verify that a required input file exists on disk.

    Args:
        filepath: Path to the expected input file.

    Returns:
        True if the file exists, False otherwise.
    """
    if not filepath.exists():
        logger.error("Required file not found: %s", filepath)
        return False
    return True


# ----------------------------------------------------------------------------
# Core Functions -- Loading & Validation
# ----------------------------------------------------------------------------
def load_dataset(filepath: Path) -> Optional[pd.DataFrame]:
    """Load the labeled training dataset produced by generate_risk_labels.py.

    Args:
        filepath: Path to `labeled_training_dataset.csv`.

    Returns:
        The loaded DataFrame, or None if the file could not be read.
    """
    try:
        df = pd.read_csv(filepath, parse_dates=["Date"])
    except Exception:
        logger.error("Failed to load dataset: %s", filepath, exc_info=True)
        return None

    logger.info("Dataset loaded from %s", filepath)
    return df


def validate_dataset(df: pd.DataFrame) -> bool:
    """Run all validation checks required before training.

    Checks that the dataset is non-empty, has no missing target
    values, has no duplicate (Stock, Date) rows, and that all
    candidate feature columns are numeric.

    Args:
        df: The loaded dataset.

    Returns:
        True only if every individual validation check passes, False
        if any check fails.
    """
    checks = {
        "dataset not empty": not df.empty,
        "no missing Risk_Level": df[TARGET_COLUMN].notna().all() if TARGET_COLUMN in df.columns else False,
        "no duplicate (Stock, Date) rows": not df.duplicated(subset=ROW_IDENTIFIER_COLUMNS).any(),
        "numeric feature columns": _validate_numeric_feature_columns(df),
    }

    for check_name, passed in checks.items():
        logger.info("Validation check '%s': %s", check_name, "PASSED" if passed else "FAILED")

    return all(checks.values())


def _validate_numeric_feature_columns(df: pd.DataFrame) -> bool:
    """Verify that all candidate feature columns are numeric.

    Args:
        df: The loaded dataset.

    Returns:
        True if every column except the identifier and target columns
        has a numeric dtype, False otherwise.
    """
    excluded_columns = IDENTIFIER_COLUMNS + [TARGET_COLUMN]
    candidate_columns = [col for col in df.columns if col not in excluded_columns]
    non_numeric = [col for col in candidate_columns if not pd.api.types.is_numeric_dtype(df[col])]

    if non_numeric:
        logger.error("Non-numeric feature columns found: %s", non_numeric)
        return False

    return True


# ----------------------------------------------------------------------------
# Core Functions -- Feature Selection & Encoding
# ----------------------------------------------------------------------------
def select_features(df: pd.DataFrame) -> tuple:
    """Separate the dataset into a feature matrix X and target vector y.

    Excludes identifier columns (`Stock`, `Date`) and the target
    column itself from the feature set, so only numerical engineered
    features are used for training.

    Args:
        df: The validated dataset.

    Returns:
        A tuple of (X, y) where X is a DataFrame of feature columns
        and y is a Series of raw (unencoded) Risk_Level values.
    """
    excluded_columns = IDENTIFIER_COLUMNS + [TARGET_COLUMN]
    feature_columns = [col for col in df.columns if col not in excluded_columns]

    X = df[feature_columns].copy()
    y = df[TARGET_COLUMN].copy()

    logger.info("Features used (%d): %s", len(feature_columns), feature_columns)
    logger.info("Target distribution:\n%s", y.value_counts().to_string())

    return X, y


def encode_labels(y: pd.Series) -> tuple:
    """Encode string Risk_Level values into integer labels.

    Args:
        y: A Series of raw (unencoded) Risk_Level values.

    Returns:
        A tuple of (y_encoded, label_encoder) where y_encoded is a
        numpy array of integer-encoded labels and label_encoder is
        the fitted `LabelEncoder`.
    """
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    logger.info("Encoded classes: %s", dict(enumerate(label_encoder.classes_)))
    return y_encoded, label_encoder


# ----------------------------------------------------------------------------
# Core Functions -- Splitting & Training
# ----------------------------------------------------------------------------
def split_dataset(X: pd.DataFrame, y_encoded: np.ndarray) -> tuple:
    """Split features and encoded target into train and test sets.

    Uses an 80/20 split, stratified by the encoded target so class
    proportions are preserved in both splits.

    Args:
        X: The feature matrix.
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


def train_model(X_train: pd.DataFrame, y_train: np.ndarray) -> Optional[RandomForestClassifier]:
    """Train a Random Forest classifier on the training split.

    Args:
        X_train: Training feature matrix.
        y_train: Training target vector (encoded).

    Returns:
        The fitted `RandomForestClassifier`, or None if training
        failed.
    """
    model = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    logger.info("Training started: RandomForestClassifier(n_estimators=%d, max_depth=%s)", N_ESTIMATORS, MAX_DEPTH)

    try:
        model.fit(X_train, y_train)
    except Exception:
        logger.error("Model training failed.", exc_info=True)
        return None

    logger.info("Training completed.")
    return model


# ----------------------------------------------------------------------------
# Core Functions -- Evaluation
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
        X_test: Test feature matrix.
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


def cross_validate_model(model: RandomForestClassifier, X: pd.DataFrame, y_encoded: np.ndarray) -> np.ndarray:
    """Run stratified 5-fold cross-validation on the training data.

    A fresh, identically-configured (unfitted) model is used for
    cross-validation so the already-fitted `model` passed elsewhere
    is not disturbed.

    Args:
        model: A fitted (or unfitted) `RandomForestClassifier` whose
            hyperparameters will be reused for a fresh estimator.
        X: Feature matrix to cross-validate on (the training split).
        y_encoded: Encoded target vector to cross-validate on.

    Returns:
        An array of per-fold accuracy scores.
    """
    fresh_model = RandomForestClassifier(**model.get_params())
    scores = cross_val_score(fresh_model, X, y_encoded, cv=CV_FOLDS, scoring="accuracy")

    logger.info(
        "Cross-validation (%d-fold) accuracy scores: %s | Mean: %.4f | Std: %.4f",
        CV_FOLDS,
        np.round(scores, 4).tolist(),
        scores.mean(),
        scores.std(),
    )

    return scores


# ----------------------------------------------------------------------------
# Visualization Functions
# ----------------------------------------------------------------------------
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


def save_encoder(label_encoder: LabelEncoder) -> Optional[Path]:
    """Persist the fitted label encoder using joblib.

    Args:
        label_encoder: The fitted `LabelEncoder`.

    Returns:
        The path the encoder was saved to, or None if saving failed.
    """
    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(label_encoder, ENCODER_FILEPATH)
    except Exception:
        logger.error("Failed to save label encoder to %s", ENCODER_FILEPATH, exc_info=True)
        return None

    return ENCODER_FILEPATH


def save_report(metrics: dict, cv_scores: np.ndarray) -> Optional[Path]:
    """Write a plain-text evaluation report to disk.

    Args:
        metrics: The dict returned by `evaluate_model`.
        cv_scores: Per-fold cross-validation accuracy scores.

    Returns:
        The path the report was saved to, or None if saving failed.
    """
    lines = [
        "Risk Classifier -- Evaluation Report",
        "=" * 50,
        f"Accuracy:  {metrics['accuracy']:.4f}",
        f"Precision (macro): {metrics['precision']:.4f}",
        f"Recall (macro):    {metrics['recall']:.4f}",
        f"F1 Score (macro):  {metrics['f1']:.4f}",
        "",
        f"{CV_FOLDS}-Fold Cross-Validation Accuracy Scores: {np.round(cv_scores, 4).tolist()}",
        f"Cross-Validation Mean Accuracy: {cv_scores.mean():.4f}",
        f"Cross-Validation Std Accuracy:  {cv_scores.std():.4f}",
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
# Main Function
# ----------------------------------------------------------------------------
def main() -> None:
    """Train, evaluate, and save the Version 1 risk classifier.

    Orchestrates: validate input exists -> load dataset -> validate
    dataset -> select features/target -> encode labels -> split ->
    train -> evaluate -> cross-validate -> plot -> save. Aborts early
    if the input file is missing, the dataset fails validation, or
    training fails.
    """
    logger.info("Starting risk classifier training.")

    if not validate_file_exists(INPUT_FILEPATH):
        logger.error("Aborting: required input file is missing.")
        return

    df = load_dataset(INPUT_FILEPATH)
    if df is None:
        logger.error("Aborting: dataset could not be loaded.")
        return

    logger.info("Dataset shape: %s", df.shape)

    if not validate_dataset(df):
        logger.error("Validation failed. Aborting training.")
        return

    X, y = select_features(df)
    y_encoded, label_encoder = encode_labels(y)

    X_train, X_test, y_train, y_test = split_dataset(X, y_encoded)
    logger.info("Train shape: %s | Test shape: %s", X_train.shape, X_test.shape)

    model = train_model(X_train, y_train)
    if model is None:
        logger.error("Aborting: model training failed.")
        return

    metrics = evaluate_model(model, X_test, y_test, label_encoder)
    cv_scores = cross_validate_model(model, X_train, y_train)

    plot_feature_importance(model, list(X.columns))
    plot_confusion_matrix(metrics["confusion_matrix"], metrics["class_names"])

    model_path = save_model(model)
    encoder_path = save_encoder(label_encoder)
    report_path = save_report(metrics, cv_scores)

    if model_path is None or encoder_path is None or report_path is None:
        logger.error("One or more output files failed to save.")
        return

    logger.info(
        "Files saved | Model: %s | Encoder: %s | Report: %s | Confusion matrix: %s | Feature importance: %s",
        model_path,
        encoder_path,
        report_path,
        FIGURES_DIR / CONFUSION_MATRIX_FILENAME,
        FIGURES_DIR / FEATURE_IMPORTANCE_FILENAME,
    )
    logger.info("Risk classifier training pipeline complete.")


# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    setup_logger()
    main()