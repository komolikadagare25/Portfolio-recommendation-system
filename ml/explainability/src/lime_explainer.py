"""
lime_explainer.py

Explainable AI (XAI) Module -- LIME-based Explanations for the Investor
Risk Classifier
========================================================================

This module is part of the "AI-Powered Personalized Stock Portfolio
Recommendation System" (MCA Major Project).

Responsibility
--------------
This module is responsible ONLY for LIME-based explainability. It does
not perform prediction logic, feature engineering, encoding, or
validation -- all of that already exists in ``predict_investor_risk.py``
and is reused here as-is. Its architecture and coding conventions
mirror ``shap_explainer.py`` (the SHAP explainability module already
completed for this project).

Given a raw investor questionnaire input, this module:

1. Loads the trained ``RandomForestClassifier``.
2. Reuses the existing preprocessing pipeline to obtain the encoded
   feature vector for the investor being explained.
3. Loads a background dataset (the encoded training distribution) that
   LIME's tabular explainer requires to model local feature
   perturbations.
4. Generates a LIME explanation for that single prediction using
   ``lime.lime_tabular.LimeTabularExplainer``.
5. Extracts per-feature weights for the predicted class.
6. Persists the interactive explanation as an HTML file.
7. Returns a single JSON-serializable dictionary describing the
   explanation.

Public API
----------
generate_lime_explanation(user_input: Dict[str, Any]) -> Dict[str, Any]
    The only function intended to be called by external modules
    (e.g., a Flask/FastAPI explainability endpoint).

All other functions in this module are private implementation details
(prefixed with ``_``) and must not be imported or relied upon directly
by external code.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np
import pandas as pd
from lime.lime_tabular import LimeTabularExplainer

# --------------------------------------------------------------------------- #
# Project-root path resolution
# --------------------------------------------------------------------------- #
# When this file is executed directly, Python only adds this script's own
# directory (ml/explainability/src/) to sys.path -- NOT the project root.
# That breaks the absolute import `ml.investor.src.predict_investor_risk`
# below with `ModuleNotFoundError: No module named 'ml'`.
#
# To make this module runnable both directly AND when imported normally by
# another package (e.g. a Flask/FastAPI app), we compute the project root
# relative to this file's own location and prepend it to sys.path if it is
# not already present. This file lives at:
#     <project_root>/ml/explainability/src/lime_explainer.py
# so the project root is three levels up from this file's parent directory.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ml.investor.src.predict_investor_risk import (  # noqa: E402
    compute_confidence,
    load_label_encoder,
    load_model,
    load_ordinal_encoder,
    predict_risk_class,
    preprocess_investor_input,
)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

#: Root directory where all LIME explainability artifacts are written.
#: Anchored to _PROJECT_ROOT (rather than a bare relative path) so the
#: output HTML is always saved to the correct location regardless of the
#: current working directory the script happens to be launched from.
FIGURES_DIR: Path = _PROJECT_ROOT / "ml" / "explainability" / "figures" / "lime"

#: Filename for the persisted LIME explanation.
EXPLANATION_HTML_FILENAME: str = "explanation.html"

#: Background dataset used to fit LIME's local perturbation distribution.
#: LIME's tabular explainer requires a representative sample of encoded
#: training data (not a single row) to estimate per-feature statistics.
#: This is intentionally NOT produced by this module -- it is the
#: already-encoded training split persisted by the Investor Profiling
#: pipeline (see prepare_training_data.py / train_investor_classifier.py).
#: Only read here, never fit or modified. This file's columns are the
#: 24 raw FEATURE_COLUMNS already ordinal-encoded to numeric, plus the
#: target label column (Investor_Risk_Level), which is dropped on load.
TRAINING_BACKGROUND_PATH: Path = (
    _PROJECT_ROOT / "ml" / "investor" / "data" / "processed" / "investor_train_split.csv"
)

#: Name of the target label column present in the background dataset
#: file that must be excluded before use as LIME's feature background.
TARGET_LABEL_COLUMN: str = "Investor_Risk_Level"

#: Number of top contributing features to report.
TOP_FEATURE_COUNT: int = 5

#: Number of features LIME itself is asked to surface per explanation.
#: Kept >= TOP_FEATURE_COUNT so truncation happens in this module, not
#: silently inside LIME.
LIME_NUM_FEATURES: int = 10

#: Number of synthetic perturbation samples LIME draws around the
#: instance being explained.
LIME_NUM_SAMPLES: int = 5000

#: Fixed random seed for reproducible LIME explanations across runs.
LIME_RANDOM_STATE: int = 42


# --------------------------------------------------------------------------- #
# Logger
# --------------------------------------------------------------------------- #
def _setup_logger() -> logging.Logger:
    """
    Configure and return the module-level logger.

    Uses a dedicated logger instance (named after this module) rather
    than the root logger, and avoids attaching duplicate handlers if the
    module is imported more than once within the same process.

    Returns
    -------
    logging.Logger
        A configured logger instance.
    """
    module_logger = logging.getLogger(__name__)

    if not module_logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        module_logger.addHandler(handler)
        module_logger.setLevel(logging.INFO)

    return module_logger


logger = _setup_logger()


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #
class LimeExplanationError(Exception):
    """Base exception for all errors raised by this module."""


class InvalidUserInputError(LimeExplanationError):
    """Raised when the raw user input fails basic structural validation."""


class BackgroundDataError(LimeExplanationError):
    """Raised when the LIME background training dataset cannot be loaded."""


class ExplainerInitializationError(LimeExplanationError):
    """Raised when the LIME tabular explainer cannot be constructed."""


class ExplanationGenerationError(LimeExplanationError):
    """Raised when LIME fails to generate an explanation for the instance."""


class ArtifactPersistenceError(LimeExplanationError):
    """Raised when the LIME explanation HTML cannot be saved to disk."""


# --------------------------------------------------------------------------- #
# Internal data model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LimeComputation:
    """
    Immutable bundle of everything computed for a single explanation
    request, passed between the private helper functions.

    Attributes
    ----------
    feature_names : Sequence[str]
        Ordered names of the encoded feature vector's columns.
    predicted_class_index : int
        Positional index of the predicted class within
        ``model.classes_`` / the LIME explainer's label space.
    feature_weight_pairs : Sequence[tuple]
        Raw ``(feature_description, weight)`` pairs as returned by
        LIME for the predicted class, ordered by descending absolute
        weight.
    """

    feature_names: Sequence[str]
    predicted_class_index: int
    feature_weight_pairs: Sequence[tuple]


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def _validate_user_input(user_input: Dict[str, Any]) -> None:
    """
    Perform basic structural validation on the raw user input.

    Note that deep, field-level validation (types, ranges, required
    questionnaire fields, etc.) is already handled inside
    ``preprocess_investor_input()`` and is intentionally NOT duplicated
    here. This check only guards against obviously malformed input
    before it reaches the shared preprocessing pipeline.

    Parameters
    ----------
    user_input : Dict[str, Any]
        Raw investor questionnaire input.

    Raises
    ------
    InvalidUserInputError
        If ``user_input`` is not a non-empty dictionary.
    """
    if not isinstance(user_input, dict) or not user_input:
        raise InvalidUserInputError(
            "user_input must be a non-empty dictionary of questionnaire "
            f"responses, got: {type(user_input).__name__}"
        )


def _validate_directories() -> None:
    """
    Ensure that the output directory for LIME artifacts exists, creating
    it (including any missing parent directories) if necessary.

    Raises
    ------
    ArtifactPersistenceError
        If the directory cannot be created (e.g., due to filesystem
        permission issues).
    """
    try:
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ArtifactPersistenceError(
            f"Unable to create LIME figures directory at {FIGURES_DIR}: {exc}"
        ) from exc


# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #
def _to_feature_array(encoded_features: Any) -> np.ndarray:
    """
    Convert the encoded feature representation into a 1D numpy array of
    shape (n_features,), regardless of whether the shared preprocessing
    function returns a DataFrame, Series, list, or numpy array.

    Parameters
    ----------
    encoded_features : Any
        The encoded feature vector/frame returned by
        ``preprocess_investor_input()``.

    Returns
    -------
    np.ndarray
        A 1D float array of shape (n_features,).
    """
    values = getattr(encoded_features, "values", encoded_features)
    return np.asarray(values, dtype=float).reshape(-1)


def _load_training_background(feature_names: Sequence[str]) -> np.ndarray:
    """
    Load the encoded training feature matrix used as LIME's background
    distribution.

    LIME's ``LimeTabularExplainer`` needs a representative sample of
    already-encoded training data to estimate per-feature means, scales,
    and quartiles for its local perturbation sampling -- a single
    investor's row is not sufficient. This function only reads that
    dataset; it never fits, modifies, or regenerates it.

    Parameters
    ----------
    feature_names : Sequence[str]
        The exact, ordered feature columns expected by the model (as
        produced by ``preprocess_investor_input()`` for this request),
        used to align and order the background dataset's columns.

    Returns
    -------
    np.ndarray
        A 2D float array of shape (n_training_rows, n_features).

    Raises
    ------
    BackgroundDataError
        If the background dataset file is missing, unreadable, or does
        not contain the expected feature columns.
    """
    if not TRAINING_BACKGROUND_PATH.exists():
        raise BackgroundDataError(
            "LIME background dataset not found at "
            f"{TRAINING_BACKGROUND_PATH}. LIME requires a sample of "
            "already-encoded training data (produced by the Investor "
            "Profiling pipeline) to model local feature statistics."
        )

    try:
        background_df = pd.read_csv(TRAINING_BACKGROUND_PATH)
    except Exception as exc:  # noqa: BLE001
        raise BackgroundDataError(
            f"Failed to read LIME background dataset at "
            f"{TRAINING_BACKGROUND_PATH}: {exc}"
        ) from exc

    if TARGET_LABEL_COLUMN in background_df.columns:
        background_df = background_df.drop(columns=[TARGET_LABEL_COLUMN])

    missing_columns = [col for col in feature_names if col not in background_df.columns]
    if missing_columns:
        raise BackgroundDataError(
            "LIME background dataset is missing expected feature "
            f"column(s): {missing_columns}"
        )

    aligned_df = background_df[list(feature_names)]
    return aligned_df.to_numpy(dtype=float)


def _resolve_class_index(model: Any, predicted_class_value: int) -> int:
    """
    Resolve the positional index of the predicted class within the
    model's ``classes_`` array.

    ``predict_risk_class()`` returns the raw encoded class *value* the
    model predicted. This value almost always equals its own positional
    index in ``model.classes_`` (since ``classes_`` is stored sorted
    ascending for standard label-encoded targets), but it is resolved
    explicitly here rather than assumed, so this function stays correct
    even if that assumption ever breaks.

    Parameters
    ----------
    model : Any
        The trained ``RandomForestClassifier`` instance.
    predicted_class_value : int
        The encoded class value returned by ``predict_risk_class()``.

    Returns
    -------
    int
        Index of the predicted class within ``model.classes_``.

    Raises
    ------
    ExplainerInitializationError
        If the predicted class value cannot be located among the
        model's known classes.
    """
    classes = np.asarray(model.classes_)
    matches = np.where(classes == predicted_class_value)[0]

    if matches.size == 0:
        raise ExplainerInitializationError(
            f"Predicted class {predicted_class_value!r} not found among "
            f"model classes {classes.tolist()}."
        )

    return int(matches[0])


def _resolve_class_names(model: Any, label_encoder: Any) -> List[str]:
    """
    Resolve human-readable class names in the exact order of
    ``model.classes_``, for use as LIME's ``class_names``.

    LIME indexes ``class_names`` positionally against the columns of
    ``model.predict_proba()``'s output, which follow ``model.classes_``
    order -- not necessarily the order of ``label_encoder.classes_``.
    Using the wrong order would silently mislabel every explanation, so
    this function derives the mapping explicitly via
    ``label_encoder.inverse_transform``.

    Parameters
    ----------
    model : Any
        The trained ``RandomForestClassifier`` instance.
    label_encoder : Any
        The already-fitted target ``LabelEncoder``.

    Returns
    -------
    List[str]
        Class names ordered to match ``model.classes_``.
    """
    return [str(name) for name in label_encoder.inverse_transform(model.classes_)]


# --------------------------------------------------------------------------- #
# LIME explanation generation
# --------------------------------------------------------------------------- #
def _build_lime_explainer(
    background: np.ndarray, feature_names: Sequence[str], class_names: Sequence[str]
) -> LimeTabularExplainer:
    """
    Construct a ``LimeTabularExplainer`` fitted to the encoded training
    background distribution.

    Parameters
    ----------
    background : np.ndarray
        Encoded training feature matrix, shape (n_training_rows,
        n_features).
    feature_names : Sequence[str]
        Ordered feature column names matching ``background``'s columns.
    class_names : Sequence[str]
        Human-readable class names ordered to match ``model.classes_``.

    Returns
    -------
    LimeTabularExplainer
        The constructed explainer, ready to explain individual
        instances.

    Raises
    ------
    ExplainerInitializationError
        If the explainer cannot be constructed.
    """
    try:
        return LimeTabularExplainer(
            training_data=background,
            feature_names=list(feature_names),
            class_names=list(class_names),
            mode="classification",
            discretize_continuous=True,
            random_state=LIME_RANDOM_STATE,
        )
    except Exception as exc:  # noqa: BLE001
        raise ExplainerInitializationError(
            f"Failed to construct LimeTabularExplainer: {exc}"
        ) from exc


def _generate_lime_explanation(
    explainer: LimeTabularExplainer,
    model: Any,
    instance: np.ndarray,
    predicted_class_index: int,
) -> Any:
    """
    Generate a LIME explanation for a single encoded investor instance.

    Parameters
    ----------
    explainer : LimeTabularExplainer
        The fitted LIME tabular explainer.
    model : Any
        The trained ``RandomForestClassifier`` instance, used via its
        ``predict_proba`` method as LIME's black-box prediction
        function.
    instance : np.ndarray
        The encoded feature vector for the investor being explained,
        shape (n_features,).
    predicted_class_index : int
        Index of the predicted class within ``model.classes_``, used to
        request the corresponding explanation label from LIME.

    Returns
    -------
    Any
        The LIME ``Explanation`` object for this instance.

    Raises
    ------
    ExplanationGenerationError
        If LIME fails to generate an explanation for the instance.
    """
    try:
        return explainer.explain_instance(
            data_row=instance,
            predict_fn=model.predict_proba,
            labels=[predicted_class_index],
            num_features=LIME_NUM_FEATURES,
            num_samples=LIME_NUM_SAMPLES,
        )
    except Exception as exc:  # noqa: BLE001
        raise ExplanationGenerationError(
            f"Failed to generate LIME explanation: {exc}"
        ) from exc


def _save_explanation_html(explanation: Any) -> Path:
    """
    Persist the LIME explanation as an interactive HTML file.

    Parameters
    ----------
    explanation : Any
        The LIME ``Explanation`` object returned by
        ``_generate_lime_explanation``.

    Returns
    -------
    Path
        Filesystem path of the saved HTML file.

    Raises
    ------
    ArtifactPersistenceError
        If the HTML file cannot be written to disk.
    """
    output_path = FIGURES_DIR / EXPLANATION_HTML_FILENAME

    try:
        explanation.save_to_file(str(output_path))
    except Exception as exc:  # noqa: BLE001
        raise ArtifactPersistenceError(
            f"Failed to save LIME explanation HTML to {output_path}: {exc}"
        ) from exc

    logger.info("LIME explanation HTML saved to %s", output_path)
    return output_path


# --------------------------------------------------------------------------- #
# Top feature extraction
# --------------------------------------------------------------------------- #
def _extract_top_features(
    explanation: Any, predicted_class_index: int, top_n: int = TOP_FEATURE_COUNT
) -> List[Dict[str, Any]]:
    """
    Extract the top contributing features (by absolute weight) for the
    predicted class from a LIME explanation.

    Parameters
    ----------
    explanation : Any
        The LIME ``Explanation`` object.
    predicted_class_index : int
        Index of the predicted class within ``model.classes_``, used to
        select the correct per-class weights from LIME's output.
    top_n : int, optional
        Maximum number of features to report, by default
        ``TOP_FEATURE_COUNT``.

    Returns
    -------
    List[Dict[str, Any]]
        A list of ``{"feature": str, "weight": float}`` entries, sorted
        by descending absolute weight.
    """
    raw_pairs = explanation.as_list(label=predicted_class_index)

    sorted_pairs = sorted(raw_pairs, key=lambda pair: abs(pair[1]), reverse=True)[:top_n]

    return [
        {"feature": str(description), "weight": round(float(weight), 4)}
        for description, weight in sorted_pairs
    ]


# --------------------------------------------------------------------------- #
# Output formatting
# --------------------------------------------------------------------------- #
def _format_output(
    prediction_label: str,
    confidence: float,
    top_features: List[Dict[str, Any]],
    lime_html_path: Path,
) -> Dict[str, Any]:
    """
    Assemble the final JSON-serializable explanation dictionary returned
    to the caller.

    Parameters
    ----------
    prediction_label : str
        The human-readable predicted risk class (e.g., "Moderate").
    confidence : float
        The prediction confidence score, as computed by
        ``compute_confidence()``.
    top_features : List[Dict[str, Any]]
        Output of ``_extract_top_features()``.
    lime_html_path : Path
        Filesystem path of the saved LIME explanation HTML.

    Returns
    -------
    Dict[str, Any]
        The fully assembled, JSON-serializable explanation payload.
    """
    return {
        "risk_level": prediction_label,
        "confidence": round(float(confidence), 4),
        "top_features": top_features,
        "lime_html": str(lime_html_path),
    }


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def generate_lime_explanation(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a LIME-based explanation for a single investor risk
    prediction.

    This is the ONLY function in this module intended to be called by
    external code. It orchestrates the shared preprocessing/prediction
    pipeline (imported from ``predict_investor_risk.py``) together with
    ``lime.lime_tabular.LimeTabularExplainer`` to produce a local,
    instance-level explanation: top contributing features and a
    persisted interactive HTML report.

    Parameters
    ----------
    user_input : Dict[str, Any]
        Raw investor questionnaire responses, in the same format
        accepted by ``preprocess_investor_input()``.

    Returns
    -------
    Dict[str, Any]
        JSON-serializable dictionary with keys: ``risk_level``,
        ``confidence``, ``top_features``, and ``lime_html``.

    Raises
    ------
    InvalidUserInputError
        If ``user_input`` is malformed at the structural level.
    BackgroundDataError
        If the LIME background training dataset cannot be loaded.
    ExplainerInitializationError
        If the LIME explainer cannot be constructed for the given
        model/data.
    ExplanationGenerationError
        If LIME fails to generate an explanation for the instance.
    ArtifactPersistenceError
        If the explanation HTML cannot be saved.

    Examples
    --------
    >>> explanation = generate_lime_explanation({"gender": "Female", "age": 24, ...})
    >>> explanation["risk_level"]
    'Moderate'
    """
    logger.info("generate_lime_explanation called for a new investor input")

    _validate_user_input(user_input)
    _validate_directories()

    # Step 1: Reuse existing model/encoder loading utilities.
    model = load_model()
    ordinal_encoder = load_ordinal_encoder()
    label_encoder = load_label_encoder()

    # Step 2: Reuse existing preprocessing to obtain the encoded feature
    # vector. preprocess_investor_input() requires the model and ordinal
    # encoder as arguments (it uses model.feature_names_in_ to align
    # column order and ordinal_encoder.transform() to encode categoricals).
    encoded_features = preprocess_investor_input(
        user_input=user_input,
        model=model,
        ordinal_encoder=ordinal_encoder,
    )
    feature_names = [str(column) for column in encoded_features.columns]
    instance = _to_feature_array(encoded_features)

    # Reuse existing prediction utilities to determine the predicted class
    # and confidence, rather than re-implementing model inference here.
    predicted_class_value, probabilities = predict_risk_class(model, encoded_features)
    confidence = compute_confidence(probabilities, predicted_class_value)
    prediction_label = str(label_encoder.inverse_transform([predicted_class_value])[0])

    predicted_class_index = _resolve_class_index(model, predicted_class_value)
    class_names = _resolve_class_names(model, label_encoder)

    # Step 3: Load the background distribution LIME needs for sampling.
    background = _load_training_background(feature_names)

    # Step 3 (cont.): Build the explainer and generate the explanation.
    explainer = _build_lime_explainer(background, feature_names, class_names)
    explanation = _generate_lime_explanation(
        explainer=explainer,
        model=model,
        instance=instance,
        predicted_class_index=predicted_class_index,
    )

    # Step 4: Extract per-feature weights for the predicted class.
    top_features = _extract_top_features(explanation, predicted_class_index)

    # Step 5: Persist the explanation as an interactive HTML file.
    lime_html_path = _save_explanation_html(explanation)

    # Step 6: Assemble the final response payload.
    result = _format_output(
        prediction_label=prediction_label,
        confidence=confidence,
        top_features=top_features,
        lime_html_path=lime_html_path,
    )

    logger.info(
        "LIME explanation generated successfully for risk_level=%r",
        result["risk_level"],
    )
    return result


# --------------------------------------------------------------------------- #
# Main / sample usage
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import json

    # NOTE: These keys must exactly match FEATURE_COLUMNS in
    # predict_investor_risk.py (the same 24 raw survey fields that
    # module's own __main__ example uses) -- this module performs no
    # feature engineering of its own and simply passes user_input
    # through to preprocess_investor_input().
    sample_user_input: Dict[str, Any] = {
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

    try:
        explanation_result = generate_lime_explanation(sample_user_input)
        print(json.dumps(explanation_result, indent=4))
    except LimeExplanationError as exc:
        logger.error("Failed to generate LIME explanation: %s", exc)