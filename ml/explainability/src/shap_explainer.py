"""
shap_explainer.py

Explainable AI (XAI) Module — SHAP-based Explanations for the Investor
Risk Classifier
========================================================================

This module is part of the "AI-Powered Personalized Stock Portfolio
Recommendation System" (MCA Major Project).

Responsibility
--------------
This module is responsible ONLY for explainability. It does not perform
prediction logic, feature engineering, encoding, or validation — all of
that already exists in ``predict_investor_risk.py`` and is reused here
as-is.

Given a raw investor questionnaire input, this module:

1. Reuses the existing preprocessing pipeline to obtain the encoded
   feature vector.
2. Reuses the existing prediction pipeline to obtain the predicted risk
   class and confidence score.
3. Computes SHAP values for that single prediction using
   ``shap.TreeExplainer`` (appropriate for the tree-based
   ``RandomForestClassifier``).
4. Renders and persists three plots (summary, bar, waterfall) to disk.
5. Extracts the top positive and top negative contributing features.
6. Returns a single JSON-serializable dictionary describing the
   explanation.

Public API
----------
generate_shap_explanation(user_input: Dict[str, Any]) -> Dict[str, Any]
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

# --------------------------------------------------------------------------- #
# Project-root path resolution
# --------------------------------------------------------------------------- #
# When this file is executed directly (e.g. `python shap_explainer.py` or the
# VS Code "Run Python File" button), Python only adds this script's own
# directory (ml/explainability/src/) to sys.path — NOT the project root. That
# breaks the absolute import `ml.investor.src.predict_investor_risk` below
# with `ModuleNotFoundError: No module named 'ml'`.
#
# To make this module runnable both directly AND when imported normally by
# another package (e.g. a Flask/FastAPI app), we compute the project root
# relative to this file's own location and prepend it to sys.path if it is
# not already present. This file lives at:
#     <project_root>/ml/explainability/src/shap_explainer.py
# so the project root is three levels up from this file's parent directory.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import matplotlib

matplotlib.use("Agg")  # Headless backend — safe for servers/CI, no display needed.
import matplotlib.pyplot as plt  # noqa: E402  (import after backend selection)
import numpy as np  # noqa: E402
import shap  # noqa: E402

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

#: Root directory where all SHAP explainability artifacts are written.
#: Anchored to _PROJECT_ROOT (rather than a bare relative path) so plots are
#: always saved to the correct location regardless of the current working
#: directory the script happens to be launched from.
FIGURES_DIR: Path = _PROJECT_ROOT / "ml" / "explainability" / "figures" / "shap"

#: Filenames for each generated plot (relative to FIGURES_DIR).
SUMMARY_PLOT_FILENAME: str = "summary_plot.png"
BAR_PLOT_FILENAME: str = "bar_plot.png"
WATERFALL_PLOT_FILENAME: str = "waterfall_plot.png"

#: Number of top contributing features to report in each direction.
TOP_FEATURE_COUNT: int = 5

#: DPI used when saving figures to disk.
PLOT_DPI: int = 150

#: Figure size (inches) applied consistently across all generated plots.
PLOT_FIGSIZE: tuple = (10, 6)


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
class ShapExplanationError(Exception):
    """Base exception for all errors raised by this module."""


class InvalidUserInputError(ShapExplanationError):
    """Raised when the raw user input fails basic structural validation."""


class ExplainerInitializationError(ShapExplanationError):
    """Raised when the SHAP TreeExplainer cannot be constructed."""


class PlotGenerationError(ShapExplanationError):
    """Raised when a SHAP plot cannot be generated or persisted to disk."""


# --------------------------------------------------------------------------- #
# Internal data model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ShapComputation:
    """
    Immutable bundle of everything computed for a single explanation
    request, passed between the private helper functions.

    Attributes
    ----------
    feature_names : Sequence[str]
        Ordered names of the encoded feature vector's columns.
    feature_values : np.ndarray
        The encoded feature vector for the single prediction being
        explained, shape (n_features,).
    shap_values : np.ndarray
        SHAP values for the predicted class, shape (n_features,).
    base_value : float
        The SHAP explainer's expected value (baseline) for the predicted
        class.
    predicted_class_index : int
        Index of the predicted class within the model's ``classes_``.
    """

    feature_names: Sequence[str]
    feature_values: np.ndarray
    shap_values: np.ndarray
    base_value: float
    predicted_class_index: int


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
    Ensure that the output directory for SHAP figures exists, creating it
    (including any missing parent directories) if necessary.

    Raises
    ------
    PlotGenerationError
        If the directory cannot be created (e.g., due to filesystem
        permission issues).
    """
    try:
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise PlotGenerationError(
            f"Unable to create SHAP figures directory at {FIGURES_DIR}: {exc}"
        ) from exc


# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #
def _resolve_feature_names(encoded_features: Any) -> List[str]:
    """
    Resolve human-readable feature names from the encoded feature
    representation produced by ``preprocess_investor_input()``.

    Supports both pandas DataFrames (uses ``.columns``) and plain
    array-likes (falls back to positional names) so this module does not
    assume a specific return type from the shared preprocessing
    function beyond it being array-convertible.

    Parameters
    ----------
    encoded_features : Any
        The encoded feature vector/frame returned by
        ``preprocess_investor_input()``.

    Returns
    -------
    List[str]
        Feature names aligned with the columns of the encoded feature
        vector.
    """
    columns = getattr(encoded_features, "columns", None)
    if columns is not None:
        return [str(column) for column in columns]

    n_features = np.asarray(encoded_features).reshape(1, -1).shape[1]
    return [f"feature_{index}" for index in range(n_features)]


def _to_feature_array(encoded_features: Any) -> np.ndarray:
    """
    Convert the encoded feature representation into a 2D numpy array of
    shape (1, n_features), regardless of whether the shared preprocessing
    function returns a DataFrame, Series, list, or numpy array.

    Parameters
    ----------
    encoded_features : Any
        The encoded feature vector/frame returned by
        ``preprocess_investor_input()``.

    Returns
    -------
    np.ndarray
        A 2D float array of shape (1, n_features).
    """
    values = getattr(encoded_features, "values", encoded_features)
    array = np.asarray(values, dtype=float).reshape(1, -1)
    return array


def _resolve_class_index(model: Any, predicted_class_index: int) -> int:
    """
    Resolve the positional index of the predicted class within the
    model's ``classes_`` array.

    ``predict_risk_class()`` returns ``int(model.predict(X)[0])`` — the
    raw encoded class *value* the model predicted. For a scikit-learn
    classifier trained on label-encoded integer targets this value
    almost always equals its own positional index in ``model.classes_``
    (since ``classes_`` is stored sorted ascending), but we resolve it
    explicitly here rather than assuming that equivalence, so this
    function stays correct even if that assumption ever breaks (e.g. a
    non-contiguous or non-zero-based label encoding).

    Parameters
    ----------
    model : Any
        The trained ``RandomForestClassifier`` instance.
    predicted_class_index : int
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
    matches = np.where(classes == predicted_class_index)[0]

    if matches.size == 0:
        raise ExplainerInitializationError(
            f"Predicted class {predicted_class_index!r} not found among "
            f"model classes {classes.tolist()}."
        )

    return int(matches[0])


# --------------------------------------------------------------------------- #
# SHAP value generation
# --------------------------------------------------------------------------- #
def _generate_shap_values(
    model: Any, feature_array: np.ndarray, predicted_class_index: int
) -> Sequence[np.ndarray]:
    """
    Construct a ``shap.TreeExplainer`` for the trained RandomForest model
    and compute SHAP values for a single encoded observation.

    Parameters
    ----------
    model : Any
        The trained ``RandomForestClassifier`` instance.
    feature_array : np.ndarray
        Encoded feature vector of shape (1, n_features).
    predicted_class_index : int
        Index of the predicted class within ``model.classes_``, used to
        select the correct SHAP values / base value when the explainer
        returns per-class outputs.

    Returns
    -------
    Sequence[np.ndarray]
        A tuple of ``(shap_values_for_class, base_value_for_class)``.

    Raises
    ------
    ExplainerInitializationError
        If the TreeExplainer cannot be constructed or SHAP values cannot
        be computed (e.g., due to an incompatible model type).
    """
    try:
        explainer = shap.TreeExplainer(model)
        raw_shap_values = explainer.shap_values(feature_array)
        raw_base_values = explainer.expected_value
    except Exception as exc:  # noqa: BLE001 - re-raised as a domain error
        raise ExplainerInitializationError(
            f"Failed to compute SHAP values using TreeExplainer: {exc}"
        ) from exc

    # shap.TreeExplainer.shap_values() historically returns a list of
    # per-class arrays for multi-class classifiers, but newer SHAP
    # versions may return a single 3D array of shape
    # (n_samples, n_features, n_classes). Both layouts are handled below.
    if isinstance(raw_shap_values, list):
        shap_values_for_class = raw_shap_values[predicted_class_index][0]
        base_value_for_class = np.asarray(raw_base_values).reshape(-1)[
            predicted_class_index
        ]
    else:
        shap_array = np.asarray(raw_shap_values)
        if shap_array.ndim == 3:
            shap_values_for_class = shap_array[0, :, predicted_class_index]
            base_value_for_class = np.asarray(raw_base_values).reshape(-1)[
                predicted_class_index
            ]
        else:
            shap_values_for_class = shap_array[0]
            base_value_for_class = np.asarray(raw_base_values).reshape(-1)[0]

    return shap_values_for_class, float(base_value_for_class)


# --------------------------------------------------------------------------- #
# Plot generators
# --------------------------------------------------------------------------- #
def _save_summary_plot(computation: ShapComputation) -> Path:
    """
    Generate and persist a SHAP summary (beeswarm-style, single-sample)
    bar plot showing the magnitude of each feature's contribution.

    Parameters
    ----------
    computation : ShapComputation
        The computed SHAP values and associated metadata.

    Returns
    -------
    Path
        Filesystem path of the saved summary plot image.

    Raises
    ------
    PlotGenerationError
        If the plot cannot be rendered or saved.
    """
    output_path = FIGURES_DIR / SUMMARY_PLOT_FILENAME

    try:
        plt.figure(figsize=PLOT_FIGSIZE)
        shap.summary_plot(
            computation.shap_values.reshape(1, -1),
            computation.feature_values.reshape(1, -1),
            feature_names=computation.feature_names,
            show=False,
            plot_type="bar",
        )
        plt.tight_layout()
        plt.savefig(output_path, dpi=PLOT_DPI, bbox_inches="tight")
    except Exception as exc:  # noqa: BLE001
        raise PlotGenerationError(f"Failed to generate summary plot: {exc}") from exc
    finally:
        plt.close("all")

    logger.info("Summary plot saved to %s", output_path)
    return output_path


def _save_bar_plot(computation: ShapComputation) -> Path:
    """
    Generate and persist a horizontal bar plot of SHAP values for the
    single explained prediction, ranked by absolute impact.

    Parameters
    ----------
    computation : ShapComputation
        The computed SHAP values and associated metadata.

    Returns
    -------
    Path
        Filesystem path of the saved bar plot image.

    Raises
    ------
    PlotGenerationError
        If the plot cannot be rendered or saved.
    """
    output_path = FIGURES_DIR / BAR_PLOT_FILENAME

    try:
        order = np.argsort(np.abs(computation.shap_values))[::-1]
        sorted_names = [computation.feature_names[i] for i in order]
        sorted_values = computation.shap_values[order]
        colors = ["#2e7d32" if value >= 0 else "#c62828" for value in sorted_values]

        plt.figure(figsize=PLOT_FIGSIZE)
        y_positions = np.arange(len(sorted_names))
        plt.barh(y_positions, sorted_values, color=colors)
        plt.yticks(y_positions, sorted_names)
        plt.gca().invert_yaxis()
        plt.xlabel("SHAP value (impact on model output)")
        plt.title("Feature Contributions to Prediction")
        plt.tight_layout()
        plt.savefig(output_path, dpi=PLOT_DPI, bbox_inches="tight")
    except Exception as exc:  # noqa: BLE001
        raise PlotGenerationError(f"Failed to generate bar plot: {exc}") from exc
    finally:
        plt.close("all")

    logger.info("Bar plot saved to %s", output_path)
    return output_path


def _save_waterfall_plot(computation: ShapComputation) -> Path:
    """
    Generate and persist a SHAP waterfall plot illustrating how each
    feature pushes the prediction away from the baseline (expected)
    value toward the final predicted value.

    Parameters
    ----------
    computation : ShapComputation
        The computed SHAP values and associated metadata.

    Returns
    -------
    Path
        Filesystem path of the saved waterfall plot image.

    Raises
    ------
    PlotGenerationError
        If the plot cannot be rendered or saved.
    """
    output_path = FIGURES_DIR / WATERFALL_PLOT_FILENAME

    try:
        explanation = shap.Explanation(
            values=computation.shap_values,
            base_values=computation.base_value,
            data=computation.feature_values,
            feature_names=list(computation.feature_names),
        )

        plt.figure(figsize=PLOT_FIGSIZE)
        shap.plots.waterfall(explanation, show=False)
        plt.tight_layout()
        plt.savefig(output_path, dpi=PLOT_DPI, bbox_inches="tight")
    except Exception as exc:  # noqa: BLE001
        raise PlotGenerationError(
            f"Failed to generate waterfall plot: {exc}"
        ) from exc
    finally:
        plt.close("all")

    logger.info("Waterfall plot saved to %s", output_path)
    return output_path


# --------------------------------------------------------------------------- #
# Top feature extraction
# --------------------------------------------------------------------------- #
def _extract_top_features(
    computation: ShapComputation, top_n: int = TOP_FEATURE_COUNT
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Identify the top positively- and negatively-contributing features for
    the explained prediction.

    Parameters
    ----------
    computation : ShapComputation
        The computed SHAP values and associated metadata.
    top_n : int, optional
        Maximum number of features to report per direction, by default
        ``TOP_FEATURE_COUNT``.

    Returns
    -------
    Dict[str, List[Dict[str, Any]]]
        A dictionary with two keys, ``"positive"`` and ``"negative"``,
        each mapping to a list of ``{"feature": str, "impact": float}``
        entries sorted by descending absolute impact.
    """
    feature_impact_pairs = list(zip(computation.feature_names, computation.shap_values))

    positive_pairs = sorted(
        (pair for pair in feature_impact_pairs if pair[1] > 0),
        key=lambda pair: abs(pair[1]),
        reverse=True,
    )[:top_n]

    negative_pairs = sorted(
        (pair for pair in feature_impact_pairs if pair[1] < 0),
        key=lambda pair: abs(pair[1]),
        reverse=True,
    )[:top_n]

    return {
        "positive": [
            {"feature": name, "impact": round(float(impact), 4)}
            for name, impact in positive_pairs
        ],
        "negative": [
            {"feature": name, "impact": round(float(impact), 4)}
            for name, impact in negative_pairs
        ],
    }


# --------------------------------------------------------------------------- #
# Output formatting
# --------------------------------------------------------------------------- #
def _format_output(
    prediction_label: str,
    confidence: float,
    top_features: Dict[str, List[Dict[str, Any]]],
    plot_paths: Dict[str, Path],
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
    top_features : Dict[str, List[Dict[str, Any]]]
        Output of ``_extract_top_features()``.
    plot_paths : Dict[str, Path]
        Mapping of plot identifiers to their saved filesystem paths.

    Returns
    -------
    Dict[str, Any]
        The fully assembled, JSON-serializable explanation payload.
    """
    return {
        "risk_level": prediction_label,
        "confidence": round(float(confidence), 4),
        "top_positive_features": top_features["positive"],
        "top_negative_features": top_features["negative"],
        "plots": {
            "summary_plot": str(plot_paths["summary"]),
            "bar_plot": str(plot_paths["bar"]),
            "waterfall_plot": str(plot_paths["waterfall"]),
        },
    }


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def generate_shap_explanation(user_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a SHAP-based explanation for a single investor risk
    prediction.

    This is the ONLY function in this module intended to be called by
    external code. It orchestrates the shared preprocessing/prediction
    pipeline (imported from ``predict_investor_risk.py``) together with
    SHAP's ``TreeExplainer`` to produce a full explanation: top
    contributing features in both directions, and three persisted plots
    (summary, bar, waterfall).

    Parameters
    ----------
    user_input : Dict[str, Any]
        Raw investor questionnaire responses, in the same format
        accepted by ``preprocess_investor_input()``.

    Returns
    -------
    Dict[str, Any]
        JSON-serializable dictionary with keys: ``risk_level  ``,
        ``confidence``, ``top_positive_features``,
        ``top_negative_features``, and ``plots``.

    Raises
    ------
    InvalidUserInputError
        If ``user_input`` is malformed at the structural level.
    ExplainerInitializationError
        If SHAP values cannot be computed for the given model/input.
    PlotGenerationError
        If any of the three plots cannot be generated or saved.

    Examples
    --------
    >>> explanation = generate_shap_explanation({"gender": "Female", "age": 24, ...})
    >>> explanation["risk_level"]
    'Moderate'
    """
    logger.info("generate_shap_explanation called for a new investor input")

    _validate_user_input(user_input)
    _validate_directories()

    # Step 1 & 2: Reuse existing model/encoder loading utilities.
    model = load_model()
    label_encoder = load_label_encoder()
    ordinal_encoder = load_ordinal_encoder()

    # Step 3: Reuse existing preprocessing to obtain the encoded feature vector.
    # NOTE: preprocess_investor_input() in predict_investor_risk.py requires
    # the loaded model and ordinal_encoder as explicit arguments (it does not
    # load them internally), so both are passed through here.
    encoded_features = preprocess_investor_input(user_input, model, ordinal_encoder)
    feature_names = _resolve_feature_names(encoded_features)
    feature_array = _to_feature_array(encoded_features)

    # Reuse existing prediction utilities to determine the predicted class
    # and confidence, rather than re-implementing model inference here.
    # predict_risk_class() returns (predicted_class_index, probabilities);
    # compute_confidence() takes that same (probabilities, index) pair.
    predicted_class_value, probabilities = predict_risk_class(model, encoded_features)
    confidence = compute_confidence(probabilities, predicted_class_value)
    prediction_label = label_encoder.inverse_transform([predicted_class_value])[0]

    predicted_class_index = _resolve_class_index(model, predicted_class_value)

    # Step 4: Compute SHAP values for the predicted class.
    shap_values, base_value = _generate_shap_values(
        model=model,
        feature_array=feature_array,
        predicted_class_index=predicted_class_index,
    )

    computation = ShapComputation(
        feature_names=feature_names,
        feature_values=feature_array.reshape(-1),
        shap_values=np.asarray(shap_values, dtype=float),
        base_value=base_value,
        predicted_class_index=predicted_class_index,
    )

    # Step 5 & 6: Generate and persist all three plots.
    plot_paths = {
        "summary": _save_summary_plot(computation),
        "bar": _save_bar_plot(computation),
        "waterfall": _save_waterfall_plot(computation),
    }

    # Step 10: Extract top contributing features in each direction.
    top_features = _extract_top_features(computation)

    # Step 11: Assemble the final response payload.
    result = _format_output(
        prediction_label=str(prediction_label),
        confidence=confidence,
        top_features=top_features,
        plot_paths=plot_paths,
    )

    logger.info(
        "SHAP explanation generated successfully for risk_level=%r",
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
    # module's own __main__ example uses) — this module performs no
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
        explanation_result = generate_shap_explanation(sample_user_input)
        print(json.dumps(explanation_result, indent=4))
    except ShapExplanationError as exc:
        logger.error("Failed to generate SHAP explanation: %s", exc)