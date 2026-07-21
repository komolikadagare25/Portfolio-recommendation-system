"""Evaluate the trained investor risk classifier without retraining.

This module is a standalone evaluation stage for the Investor
Profiling pipeline (sharing the same architecture and coding
conventions as the rest of the pipeline). Its sole responsibility is
to load the already-trained Random Forest classifier, its fitted
LabelEncoder and OrdinalEncoder, and the held-out train/test splits
produced by `train_investor_classifier.py`, generate predictions, and
report a thorough set of evaluation metrics and diagnostics.

This module MUST NOT:
    * Fit, retrain, or tune any model or encoder.
    * Regenerate the train/test split (the exact split persisted by
      train_investor_classifier.py is loaded, not recomputed).

Typical usage:
    python -m src.evaluate_investor_classifier
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
from sklearn.preprocessing import LabelEncoder, OrdinalEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    cohen_kappa_score,
    matthews_corrcoef,
)

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
# ml/investor/src/evaluate_investor_classifier.py -> parent (src) -> parent (investor)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Directory holding the trained model and fitted encoders.
MODELS_DIR: Final[Path] = BASE_DIR / "models"

#: Trained classifier, produced by train_investor_classifier.py.
MODEL_FILEPATH: Final[Path] = MODELS_DIR / "investor_risk_classifier.pkl"

#: Fitted target LabelEncoder, produced by train_investor_classifier.py.
LABEL_ENCODER_FILEPATH: Final[Path] = MODELS_DIR / "label_encoder.pkl"

#: Fitted feature OrdinalEncoder, produced by train_investor_classifier.py.
ORDINAL_ENCODER_FILEPATH: Final[Path] = MODELS_DIR / "ordinal_encoder.pkl"

#: Directory holding the held-out train/test splits.
PROCESSED_DATA_DIR: Final[Path] = BASE_DIR / "data" / "processed"

#: Encoded training split (features + original string target), as
#: persisted by train_investor_classifier.py.
TRAIN_SPLIT_FILEPATH: Final[Path] = PROCESSED_DATA_DIR / "investor_train_split.csv"

#: Encoded test split (features + original string target), as
#: persisted by train_investor_classifier.py.
TEST_SPLIT_FILEPATH: Final[Path] = PROCESSED_DATA_DIR / "investor_test_split.csv"

#: Target column name, matching the rest of the pipeline.
TARGET_COLUMN: Final[str] = "Investor_Risk_Level"

#: Directory where this module's own reports are saved.
REPORTS_DIR: Final[Path] = BASE_DIR / "reports"

#: Output path for this module's evaluation report. Named distinctly
#: from classification_report.txt (written by
#: train_investor_classifier.py) so this module never overwrites it.
EVALUATION_REPORT_FILEPATH: Final[Path] = REPORTS_DIR / "evaluation_report.txt"

#: Directory where this module's own figures are saved.
FIGURES_DIR: Final[Path] = REPORTS_DIR / "figures"

#: Filenames for this module's figures, distinct from the training
#: module's confusion_matrix.png / feature_importance.png so neither
#: run overwrites the other's output.
EVALUATION_CONFUSION_MATRIX_FILENAME: Final[str] = "evaluation_confusion_matrix.png"
EVALUATION_FEATURE_IMPORTANCE_FILENAME: Final[str] = "evaluation_feature_importance.png"

#: If (train_accuracy - test_accuracy) exceeds this, the model is
#: flagged as showing signs of overfitting. Matches the threshold used
#: in train_investor_classifier.py so both modules agree on the
#: definition of "overfitting" for this pipeline.
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
# Validation Functions
# ----------------------------------------------------------------------------
def validate_required_files_exist() -> bool:
    """Verify that every file this module needs to load actually exists.

    Checks the trained model, both fitted encoders, and both the
    train and test split files.

    Returns:
        True if all required files exist, False otherwise (each
        missing file is logged individually).
    """
    required_files = {
        "trained model": MODEL_FILEPATH,
        "label encoder": LABEL_ENCODER_FILEPATH,
        "ordinal encoder": ORDINAL_ENCODER_FILEPATH,
        "train split": TRAIN_SPLIT_FILEPATH,
        "test split": TEST_SPLIT_FILEPATH,
    }

    all_present = True
    for description, filepath in required_files.items():
        exists = filepath.exists()
        logger.info("Validation check '%s exists' (%s): %s", description, filepath, "PASSED" if exists else "FAILED")
        if not exists:
            all_present = False

    return all_present


def validate_split_dataset(df: pd.DataFrame, split_name: str) -> bool:
    """Run validation checks on a loaded train/test split.

    Checks that the target column exists, the dataframe is non-empty,
    and no duplicate rows exist.

    Args:
        df: The loaded split DataFrame.
        split_name: A short label ("train" or "test") used only for
            logging context.

    Returns:
        True only if every individual validation check passes, False
        if any check fails.
    """
    checks = {
        "target column exists": TARGET_COLUMN in df.columns,
        "dataframe not empty": not df.empty,
        "no duplicate rows": not df.duplicated().any(),
    }

    for check_name, passed in checks.items():
        logger.info("Validation check '%s (%s split)': %s", check_name, split_name, "PASSED" if passed else "FAILED")

    return all(checks.values())


# ----------------------------------------------------------------------------
# Core Functions -- Loading
# ----------------------------------------------------------------------------
def load_model(filepath: Path) -> Optional[RandomForestClassifier]:
    """Load the already-trained classifier from disk. Does not fit anything.

    Args:
        filepath: Path to the saved model `.pkl` file.

    Returns:
        The loaded classifier, or None if it could not be read.
    """
    try:
        model = joblib.load(filepath)
    except Exception:
        logger.error("Failed to load model: %s", filepath, exc_info=True)
        return None

    logger.info("Loaded trained model from %s", filepath)
    return model


def load_label_encoder(filepath: Path) -> Optional[LabelEncoder]:
    """Load the already-fitted target LabelEncoder from disk.

    Args:
        filepath: Path to the saved encoder `.pkl` file.

    Returns:
        The loaded `LabelEncoder`, or None if it could not be read.
    """
    try:
        label_encoder = joblib.load(filepath)
    except Exception:
        logger.error("Failed to load label encoder: %s", filepath, exc_info=True)
        return None

    logger.info("Loaded label encoder from %s | Classes: %s", filepath, list(label_encoder.classes_))
    return label_encoder


def load_ordinal_encoder(filepath: Path) -> Optional[OrdinalEncoder]:
    """Load the already-fitted feature OrdinalEncoder from disk.

    The train/test splits loaded by this module are already ordinal-
    encoded (as persisted by train_investor_classifier.py), so this
    encoder is not re-applied here -- it is loaded and validated so
    its fitted categories are available and auditable, matching what
    any future raw-data inference path would need to reuse.

    Args:
        filepath: Path to the saved encoder `.pkl` file.

    Returns:
        The loaded `OrdinalEncoder`, or None if it could not be read.
    """
    try:
        ordinal_encoder = joblib.load(filepath)
    except Exception:
        logger.error("Failed to load ordinal encoder: %s", filepath, exc_info=True)
        return None

    logger.info(
        "Loaded ordinal encoder from %s | Fitted categories per column: %s",
        filepath,
        [list(cats) for cats in ordinal_encoder.categories_],
    )
    return ordinal_encoder


def load_split(filepath: Path) -> Optional[pd.DataFrame]:
    """Load a persisted train or test split from a CSV file.

    Args:
        filepath: Path to the split CSV file.

    Returns:
        The loaded DataFrame, or None if it could not be read.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception:
        logger.error("Failed to load split: %s", filepath, exc_info=True)
        return None

    logger.info("Loaded split from %s | Shape: %s", filepath, df.shape)
    return df


# ----------------------------------------------------------------------------
# Core Functions -- Prediction & Metrics
# ----------------------------------------------------------------------------
def prepare_features_and_target(df: pd.DataFrame, label_encoder: LabelEncoder) -> tuple:
    """Split a loaded split DataFrame into features and encoded target.

    Args:
        df: A loaded train or test split, containing already
            ordinal-encoded feature columns plus the original string
            `TARGET_COLUMN`.
        label_encoder: The already-fitted `LabelEncoder`, used only to
            `.transform` (never fit) the string labels.

    Returns:
        A tuple of (X, y_encoded).
    """
    X = df.drop(columns=[TARGET_COLUMN])
    y_encoded = label_encoder.transform(df[TARGET_COLUMN])
    return X, y_encoded


def generate_predictions(model: RandomForestClassifier, X: pd.DataFrame) -> np.ndarray:
    """Generate predictions for a feature matrix using an already-fitted model.

    Args:
        model: The loaded, already-fitted classifier.
        X: The feature matrix to predict on.

    Returns:
        An array of predicted encoded labels.
    """
    return model.predict(X)


def compute_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    label_encoder: LabelEncoder,
) -> dict:
    """Compute the core classification metrics on the test set.

    Args:
        y_true: True encoded test labels.
        y_pred: Predicted encoded test labels.
        label_encoder: The fitted `LabelEncoder`, used to recover
            human-readable class names for the report.

    Returns:
        A dict containing `accuracy`, `precision`, `recall`, `f1`,
        `report_text`, `confusion_matrix`, and `class_names`.
    """
    class_names = label_encoder.classes_

    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "report_text": classification_report(y_true, y_pred, target_names=class_names, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred),
        "class_names": class_names,
    }

    logger.info(
        "Test metrics | Accuracy: %.4f | Precision: %.4f | Recall: %.4f | F1: %.4f",
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
        model: The loaded, already-fitted classifier.
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


def compute_agreement_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Compute Cohen's Kappa and Matthews Correlation Coefficient.

    Both metrics account for the possibility of agreement by chance,
    complementing plain accuracy: Cohen's Kappa is the standard
    inter-rater-agreement style metric; MCC is a balanced measure that
    remains informative even under class imbalance.

    Args:
        y_true: True encoded labels.
        y_pred: Predicted encoded labels.

    Returns:
        A dict with `cohen_kappa` and `matthews_corrcoef`.
    """
    kappa = cohen_kappa_score(y_true, y_pred)
    mcc = matthews_corrcoef(y_true, y_pred)

    logger.info("Cohen's Kappa: %.4f", kappa)
    logger.info("Matthews Correlation Coefficient: %.4f", mcc)

    return {"cohen_kappa": float(kappa), "matthews_corrcoef": float(mcc)}


def detect_overfitting(model: RandomForestClassifier, X_train: pd.DataFrame, y_train: np.ndarray, X_test: pd.DataFrame, y_test: np.ndarray) -> dict:
    """Detect overfitting by comparing train and test performance.

    Args:
        model: The loaded, already-fitted classifier.
        X_train: Training feature matrix.
        y_train: Training target vector (encoded).
        X_test: Test feature matrix.
        y_test: Test target vector (encoded).

    Returns:
        A dict with `train_accuracy`, `test_accuracy`, `gap`, and
        `overfitting_detected`.
    """
    train_accuracy = accuracy_score(y_train, model.predict(X_train))
    test_accuracy = accuracy_score(y_test, model.predict(X_test))
    gap = train_accuracy - test_accuracy
    overfitting_detected = gap > OVERFITTING_GAP_THRESHOLD

    logger.info("Train accuracy: %.4f | Test accuracy: %.4f | Gap: %.4f", train_accuracy, test_accuracy, gap)
    if overfitting_detected:
        logger.warning("Possible overfitting detected: gap %.4f exceeds threshold %.4f.", gap, OVERFITTING_GAP_THRESHOLD)
    else:
        logger.info("No strong overfitting signal: gap %.4f is within threshold %.4f.", gap, OVERFITTING_GAP_THRESHOLD)

    return {
        "train_accuracy": float(train_accuracy),
        "test_accuracy": float(test_accuracy),
        "gap": float(gap),
        "overfitting_detected": bool(overfitting_detected),
    }


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
    ax.set_title("Confusion Matrix (Evaluation)")

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            text_color = "white" if cm[i, j] > cm.max() / 2 else "black"
            ax.text(j, i, str(cm[i, j]), ha="center", va="center", color=text_color)

    fig.colorbar(im, ax=ax, label="Count")
    fig.tight_layout()

    filepath = FIGURES_DIR / EVALUATION_CONFUSION_MATRIX_FILENAME
    fig.savefig(filepath)
    plt.close(fig)

    return filepath


def plot_feature_importance(model: RandomForestClassifier, feature_names: list) -> Path:
    """Create and save a descending-sorted feature importance bar chart.

    Args:
        model: The loaded, already-fitted classifier.
        feature_names: Names of the features, in the same order used
            during training.

    Returns:
        The path the figure was saved to.
    """
    importances = pd.Series(model.feature_importances_, index=feature_names).sort_values(ascending=False)

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(importances.index[::-1], importances.values[::-1])
    ax.set_title("Feature Importance (Evaluation)")
    ax.set_xlabel("Importance")
    ax.set_ylabel("Feature")
    ax.grid(True, axis="x")
    fig.tight_layout()

    filepath = FIGURES_DIR / EVALUATION_FEATURE_IMPORTANCE_FILENAME
    fig.savefig(filepath)
    plt.close(fig)

    return filepath


# ----------------------------------------------------------------------------
# Save Functions
# ----------------------------------------------------------------------------
def save_evaluation_report(
    classification_metrics: dict,
    agreement_metrics: dict,
    overfitting_summary: dict,
    roc_auc: Optional[float],
) -> Optional[Path]:
    """Write the final plain-text evaluation report to disk.

    Args:
        classification_metrics: The dict from
            `compute_classification_metrics`.
        agreement_metrics: The dict from `compute_agreement_metrics`.
        overfitting_summary: The dict from `detect_overfitting`.
        roc_auc: The macro one-vs-rest ROC-AUC, or None.

    Returns:
        The path the report was saved to, or None if saving failed.
    """
    lines = [
        "Investor Risk Classifier -- Standalone Evaluation Report",
        "=" * 55,
        f"Train accuracy:       {overfitting_summary['train_accuracy']:.4f}",
        f"Test accuracy:        {overfitting_summary['test_accuracy']:.4f}",
        f"Train-test gap:       {overfitting_summary['gap']:.4f}",
        f"Overfitting detected: {overfitting_summary['overfitting_detected']}",
        "",
        f"Accuracy:             {classification_metrics['accuracy']:.4f}",
        f"Precision (macro):    {classification_metrics['precision']:.4f}",
        f"Recall (macro):       {classification_metrics['recall']:.4f}",
        f"F1 Score (macro):     {classification_metrics['f1']:.4f}",
        f"ROC-AUC (macro, OVR): {roc_auc:.4f}" if roc_auc is not None else "ROC-AUC (macro, OVR): N/A",
        f"Cohen's Kappa:        {agreement_metrics['cohen_kappa']:.4f}",
        f"Matthews Corr. Coef.: {agreement_metrics['matthews_corrcoef']:.4f}",
        "",
        "Classification Report",
        "-" * 55,
        classification_metrics["report_text"],
    ]

    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        EVALUATION_REPORT_FILEPATH.write_text("\n".join(lines))
    except Exception:
        logger.error("Failed to save evaluation report to %s", EVALUATION_REPORT_FILEPATH, exc_info=True)
        return None

    return EVALUATION_REPORT_FILEPATH


# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------
def summarize_evaluation(
    classification_metrics: dict,
    agreement_metrics: dict,
    overfitting_summary: dict,
    roc_auc: Optional[float],
    report_path: Path,
) -> None:
    """Print and log a final summary of the standalone evaluation run.

    Args:
        classification_metrics: The dict from
            `compute_classification_metrics`.
        agreement_metrics: The dict from `compute_agreement_metrics`.
        overfitting_summary: The dict from `detect_overfitting`.
        roc_auc: The macro one-vs-rest ROC-AUC, or None.
        report_path: The path the evaluation report was saved to.
    """
    logger.info("===== Investor Risk Classifier -- Evaluation Summary =====")
    logger.info("Train accuracy: %.4f", overfitting_summary["train_accuracy"])
    logger.info("Test accuracy: %.4f", overfitting_summary["test_accuracy"])
    logger.info("Overfitting detected: %s", overfitting_summary["overfitting_detected"])
    logger.info("Accuracy: %.4f", classification_metrics["accuracy"])
    logger.info("Precision (macro): %.4f", classification_metrics["precision"])
    logger.info("Recall (macro): %.4f", classification_metrics["recall"])
    logger.info("F1 (macro): %.4f", classification_metrics["f1"])
    logger.info("Cohen's Kappa: %.4f", agreement_metrics["cohen_kappa"])
    logger.info("Matthews Correlation Coefficient: %.4f", agreement_metrics["matthews_corrcoef"])
    logger.info("Report saved to: %s", report_path)
    logger.info("============================================================")

    print("=" * 60)
    print("Investor Risk Classifier -- Evaluation Summary")
    print("=" * 60)
    print(f"Train accuracy       : {overfitting_summary['train_accuracy']:.4f}")
    print(f"Test accuracy        : {overfitting_summary['test_accuracy']:.4f}")
    print(f"Overfitting detected : {overfitting_summary['overfitting_detected']}")
    print(f"Accuracy             : {classification_metrics['accuracy']:.4f}")
    print(f"Precision (macro)    : {classification_metrics['precision']:.4f}")
    print(f"Recall (macro)       : {classification_metrics['recall']:.4f}")
    print(f"F1 (macro)           : {classification_metrics['f1']:.4f}")
    roc_display = f"{roc_auc:.4f}" if roc_auc is not None else "N/A"
    print(f"ROC-AUC (macro, OVR) : {roc_display}")
    print(f"Cohen's Kappa        : {agreement_metrics['cohen_kappa']:.4f}")
    print(f"Matthews Corr. Coef. : {agreement_metrics['matthews_corrcoef']:.4f}")
    print(f"Report save path     : {report_path}")
    print("=" * 60)


# ----------------------------------------------------------------------------
# Main Function
# ----------------------------------------------------------------------------
def main() -> None:
    """Run the standalone investor risk classifier evaluation end to end.

    Orchestrates: validate required files exist -> load model, both
    encoders, and both splits -> validate splits -> prepare features
    and targets (transform only, never fit) -> generate predictions ->
    compute classification metrics, ROC-AUC, Cohen's Kappa, and MCC on
    the test set -> detect overfitting by comparing train and test
    accuracy -> plot -> save report -> summarize. No model or encoder
    is fit or retrained anywhere in this module.
    """
    logger.info("Starting standalone investor risk classifier evaluation.")

    if not validate_required_files_exist():
        logger.error("Aborting: one or more required files are missing.")
        return

    model = load_model(MODEL_FILEPATH)
    label_encoder = load_label_encoder(LABEL_ENCODER_FILEPATH)
    ordinal_encoder = load_ordinal_encoder(ORDINAL_ENCODER_FILEPATH)

    if model is None or label_encoder is None or ordinal_encoder is None:
        logger.error("Aborting: model or encoders could not be loaded.")
        return

    train_df = load_split(TRAIN_SPLIT_FILEPATH)
    test_df = load_split(TEST_SPLIT_FILEPATH)

    if train_df is None or test_df is None:
        logger.error("Aborting: train/test split could not be loaded.")
        return

    if not validate_split_dataset(train_df, "train") or not validate_split_dataset(test_df, "test"):
        logger.error("Aborting: train/test split failed validation.")
        return

    X_train, y_train = prepare_features_and_target(train_df, label_encoder)
    X_test, y_test = prepare_features_and_target(test_df, label_encoder)

    y_pred = generate_predictions(model, X_test)

    classification_metrics = compute_classification_metrics(y_test, y_pred, label_encoder)
    roc_auc = compute_roc_auc(model, X_test, y_test)
    agreement_metrics = compute_agreement_metrics(y_test, y_pred)
    overfitting_summary = detect_overfitting(model, X_train, y_train, X_test, y_test)

    plot_confusion_matrix(classification_metrics["confusion_matrix"], classification_metrics["class_names"])
    plot_feature_importance(model, list(X_test.columns))

    report_path = save_evaluation_report(classification_metrics, agreement_metrics, overfitting_summary, roc_auc)

    if report_path is None:
        logger.error("Aborting: failed to save evaluation report.")
        return

    summarize_evaluation(classification_metrics, agreement_metrics, overfitting_summary, roc_auc, report_path)
    logger.info("Standalone investor risk classifier evaluation complete.")


# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    setup_logger()
    main()