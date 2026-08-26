"""
Bridges the FastAPI backend to the existing Python ML modules in ../ml/.

The frontend questionnaire (riskQuestions.js) now collects all 24 fields
the model needs. FIELD_NAME_MAP translates the frontend's field ids
(matching riskQuestions.js) into the lowercase snake_case names the
trained model expects (see predict_investor_risk.py). DEFAULT_FIELDS is
kept only as a safety fallback in case a field is ever missing.
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


def run_full_pipeline(questionnaire_answers: dict) -> dict:
    """Runs the entire ML pipeline and returns everything a Report needs to store."""
    model_input = build_full_model_input(questionnaire_answers)

    prediction = predict_investor_risk(model_input)
    portfolio = generate_portfolio(prediction["risk_level"], prediction["confidence"])
    shap_result = generate_shap_explanation(model_input)
    lime_result = generate_lime_explanation(model_input)

    return {
        "risk_level": prediction["risk_level"],
        "confidence": prediction["confidence"],
        "portfolio": portfolio,
        "shap": {
            "top_positive_features": shap_result["top_positive_features"],
            "top_negative_features": shap_result["top_negative_features"],
        },
        "lime": {
            "top_features": lime_result["top_features"],
        },
    }