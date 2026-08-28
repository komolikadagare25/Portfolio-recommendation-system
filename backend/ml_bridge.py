"""
Bridges the FastAPI backend to the existing Python ML modules in ../ml/.

The frontend questionnaire (riskQuestions.js) collects all 24 fields the
model needs. FIELD_NAME_MAP translates the frontend's field ids into the
lowercase snake_case names the trained model expects (see
predict_investor_risk.py). DEFAULT_FIELDS is kept only as a safety
fallback in case a field is ever missing.

On top of the base ML pipeline, this module adds a personalization layer
(personalize_allocation, blend_with_preferences) that adjusts the
risk-band template allocation using real per-user signals — confidence,
age, investment horizon, and the user's own 1-7 preference sliders — so
two users in the same risk band get genuinely different portfolios. Every
adjustment is tracked step-by-step (build_personalization_explanation) so
the final result is traceable back to real inputs, not a black box.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ml.investor.src.predict_investor_risk import predict_investor_risk
from ml.portfolio.src.portfolio_recommender import generate_portfolio
from ml.explainability.src.shap_explainer import generate_shap_explanation
from ml.explainability.src.lime_explainer import generate_lime_explanation

# Maps frontend field ids (riskQuestions.js) -> model's expected field names.
FIELD_NAME_MAP = {
    "age": "age",
    "gender": "gender",
    "Investment_Avenues": "investment_avenues",
    "Stock_Marktet": "stock_market",
    "Mutual_Funds": "mutual_funds",
    "Equity_Market": "equity_market",
    "Debentures": "debentures",
    "Government_Bonds": "government_bonds",
    "Fixed_Deposits": "fixed_deposits",
    "PPF": "ppf",
    "Gold": "gold",
    "Factor": "factor",
    "Objective": "objective",
    "Purpose": "purpose",
    "Duration": "duration",
    "Invest_Monitor": "invest_monitor",
    "Expect": "expect",
    "Avenue": "avenue",
    "Savings_Objective": "what_are_your_savings_objectives",
    "Reason_Equity": "reason_equity",
    "Reason_Mutual": "reason_mutual",
    "Reason_Bonds": "reason_bonds",
    "Reason_FD": "reason_fd",
    "Source": "source",
}

# Fallback only — used if a field is ever missing from the frontend payload.
DEFAULT_FIELDS = {
    "mutual_funds": 4,
    "equity_market": 4,
    "debentures": 4,
    "government_bonds": 4,
    "fixed_deposits": 4,
    "ppf": 4,
    "gold": 4,
    "purpose": "Wealth Creation",
    "what_are_your_savings_objectives": "Retirement Plan",
    "reason_equity": "Capital Appreciation",
    "reason_mutual": "Better Returns",
    "reason_bonds": "Assured Returns",
    "reason_fd": "Fixed Returns",
    "source": "Internet",
}


def build_full_model_input(questionnaire_answers: dict) -> dict:
    """Renames frontend field ids to the model's expected names, filling
    in a neutral default only if a field is genuinely missing."""
    model_input = {}
    for frontend_id, model_key in FIELD_NAME_MAP.items():
        if frontend_id in questionnaire_answers:
            model_input[model_key] = questionnaire_answers[frontend_id]
        elif model_key in DEFAULT_FIELDS:
            model_input[model_key] = DEFAULT_FIELDS[model_key]
        else:
            raise ValueError(f"Missing required questionnaire field: {frontend_id}")
    return model_input


# --------------------------------------------------------------------------- #
# Personalization layer (post-processing on top of the ML/rule-based output —
# portfolio_recommender.py itself is never modified).
# --------------------------------------------------------------------------- #

def _redistribute_shift(allocation: dict, target_key: str, shift: float, donor_keys: list) -> dict:
    """Moves `shift` percentage points into target_key, taken proportionally
    from donor_keys (never pushing any category below 0)."""
    result = dict(allocation)
    donor_total = sum(result[k] for k in donor_keys)
    if donor_total <= 0 or shift == 0:
        return result

    actual_shift = min(shift, donor_total) if shift > 0 else max(shift, -result[target_key])

    for k in donor_keys:
        share = result[k] / donor_total
        result[k] = max(0.0, result[k] - actual_shift * share)
    result[target_key] = max(0.0, result[target_key] + actual_shift)
    return result


def _renormalize_to_100(allocation: dict) -> dict:
    """Rescales so percentages sum to exactly 100, then rounds, putting any
    leftover rounding remainder into the largest category."""
    total = sum(allocation.values())
    if total <= 0:
        return allocation

    scaled = {k: v * 100 / total for k, v in allocation.items()}
    rounded = {k: round(v) for k, v in scaled.items()}
    remainder = 100 - sum(rounded.values())
    if remainder != 0:
        largest_key = max(rounded, key=rounded.get)
        rounded[largest_key] += remainder
    return rounded


def personalize_allocation(base_portfolio: dict, risk_level: str, confidence: float, model_input: dict) -> dict:
    """Adjusts base_portfolio['asset_allocation'] using real per-user signals
    (confidence, age, investment duration) — bounded, explainable nudges on
    top of the risk-band template, not a replacement for it."""
    allocation = {k: float(v) for k, v in base_portfolio["asset_allocation"].items()}

    # 1. Confidence-aware blending toward Moderate (skip if already Moderate).
    if risk_level in ("Conservative", "Aggressive"):
        moderate_portfolio = generate_portfolio("Moderate", confidence)
        moderate_allocation = moderate_portfolio["asset_allocation"]

        own_weight = 0.5 + confidence / 2  # 0.5 (low confidence) .. 1.0 (full confidence)
        allocation = {
            k: allocation[k] * own_weight + moderate_allocation.get(k, 0) * (1 - own_weight)
            for k in allocation
        }

    safer_keys = [k for k in ("Government Bonds", "Fixed Deposits", "Gold") if k in allocation]
    equity_key = "Stocks" if "Stocks" in allocation else None

    # 2. Age tilt.
    age = model_input.get("age")
    if equity_key and isinstance(age, (int, float)):
        if age <= 30:
            allocation = _redistribute_shift(allocation, equity_key, 5, safer_keys)
        elif age >= 50:
            allocation = _redistribute_shift(allocation, equity_key, -5, [equity_key])
            freed = 5
            for k in safer_keys:
                allocation[k] = allocation.get(k, 0) + freed / max(len(safer_keys), 1)

    # 3. Investment horizon tilt.
    duration = model_input.get("duration")
    if equity_key:
        if duration in ("Less Than 1 Year", "1-3 Years"):
            allocation = _redistribute_shift(allocation, equity_key, -5, [equity_key])
            freed = 5
            for k in safer_keys:
                allocation[k] = allocation.get(k, 0) + freed / max(len(safer_keys), 1)
        elif duration == "More Than 5 Years":
            allocation = _redistribute_shift(allocation, equity_key, 5, safer_keys)

    base_portfolio["asset_allocation"] = _renormalize_to_100(allocation)
    return base_portfolio


def _preference_based_allocation(model_input: dict) -> dict:
    """Derives an allocation directly from the user's own 1-7 preference
    sliders, normalized to sum to 100. This is the user's stated
    preference, independent of the ML risk classification."""
    raw = {
        "Stocks": model_input.get("equity_market", 4),
        "Mutual Funds": model_input.get("mutual_funds", 4),
        "Government Bonds": model_input.get("government_bonds", 4) + model_input.get("debentures", 4),
        "Fixed Deposits": model_input.get("fixed_deposits", 4) + model_input.get("ppf", 4),
        "Gold": model_input.get("gold", 4),
    }
    total = sum(raw.values())
    if total <= 0:
        return {k: 100 / len(raw) for k in raw}
    return {k: v * 100 / total for k, v in raw.items()}


def blend_with_preferences(portfolio: dict, model_input: dict, preference_weight: float = 0.5) -> dict:
    """Blends the (already confidence/age/duration-tilted) band allocation
    with an allocation derived from the user's own slider preferences, so
    two users in the same risk band get genuinely different portfolios."""
    band_allocation = {k: float(v) for k, v in portfolio["asset_allocation"].items()}
    preference_allocation = _preference_based_allocation(model_input)

    blended = {
        k: band_allocation[k] * (1 - preference_weight) + preference_allocation.get(k, 0) * preference_weight
        for k in band_allocation
    }

    portfolio["asset_allocation"] = _renormalize_to_100(blended)
    return portfolio


# --------------------------------------------------------------------------- #
# Traceability: explains exactly how/why the final allocation diverged from
# the standard risk-band template, using real computed deltas per step.
# --------------------------------------------------------------------------- #

def _diff_allocation(before: dict, after: dict, threshold: float = 1.0) -> dict:
    """Returns only the categories that changed by at least `threshold`
    percentage points between two allocation snapshots."""
    changes = {k: round(after.get(k, 0) - before.get(k, 0), 1) for k in after}
    return {k: v for k, v in changes.items() if abs(v) >= threshold}


def build_personalization_explanation(
    base_allocation: dict,
    final_allocation: dict,
    step_diffs: list,
    model_input: dict,
) -> dict:
    """Builds a plain-language, step-by-step account of how the final
    allocation diverged from the standard risk-band template — using only
    real deltas computed during the actual pipeline run."""
    overall_changes = _diff_allocation(base_allocation, final_allocation)

    sentences = []
    for step in step_diffs:
        if not step["changes"]:
            continue
        parts = [
            f"{category} {'+' if delta > 0 else ''}{delta}pts"
            for category, delta in step["changes"].items()
        ]
        sentences.append(f"{step['label']}: {', '.join(parts)}.")

    if not sentences:
        summary = "Your allocation matches the standard template for your risk band — no personalization signals shifted it meaningfully."
    else:
        summary = " ".join(sentences)

    return {
        "base_allocation": base_allocation,
        "final_allocation": final_allocation,
        "overall_changes": overall_changes,
        "steps": step_diffs,
        "summary": summary,
    }


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #

def run_full_pipeline(questionnaire_answers: dict) -> dict:
    """Runs the entire ML pipeline and returns everything a Report needs to store."""
    model_input = build_full_model_input(questionnaire_answers)

    prediction = predict_investor_risk(model_input)
    risk_level = prediction["risk_level"]
    confidence = prediction["confidence"]

    base_portfolio = generate_portfolio(risk_level, confidence)
    base_allocation = dict(base_portfolio["asset_allocation"])

    portfolio = generate_portfolio(risk_level, confidence)
    step_diffs = []

    before = dict(portfolio["asset_allocation"])
    portfolio = personalize_allocation(portfolio, risk_level, confidence, model_input)
    after = dict(portfolio["asset_allocation"])
    step_diffs.append({
        "label": "Confidence, age & investment horizon adjustment",
        "changes": _diff_allocation(before, after),
    })

    before = dict(portfolio["asset_allocation"])
    portfolio = blend_with_preferences(portfolio, model_input, preference_weight=0.5)
    after = dict(portfolio["asset_allocation"])
    step_diffs.append({
        "label": "Your stated slider preferences",
        "changes": _diff_allocation(before, after),
    })

    personalization_explanation = build_personalization_explanation(
        base_allocation, portfolio["asset_allocation"], step_diffs, model_input
    )
    portfolio["personalization_explanation"] = personalization_explanation

    shap_result = generate_shap_explanation(model_input)
    lime_result = generate_lime_explanation(model_input)

    return {
        "risk_level": risk_level,
        "confidence": confidence,
        "portfolio": portfolio,
        "shap": {
            "top_positive_features": shap_result["top_positive_features"],
            "top_negative_features": shap_result["top_negative_features"],
        },
        "lime": {
            "top_features": lime_result["top_features"],
        },
    }