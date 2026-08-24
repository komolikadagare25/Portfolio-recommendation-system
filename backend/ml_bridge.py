"""
Bridges the FastAPI backend to the existing Python ML modules in ../ml/.

The frontend questionnaire currently collects only 10 of the 24 fields
the model was trained on. The remaining 14 use neutral defaults below.
# TODO: collect these from a real questionnaire once the frontend
# supports it — see riskQuestionsReal.js on the frontend side.
"""

import sys
from pathlib import Path

# ml/ lives one directory above backend/, so add the project root to
# sys.path the same way demo/app.py does.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ml.investor.src.predict_investor_risk import predict_investor_risk
from ml.portfolio.src.portfolio_recommender import generate_portfolio
from ml.explainability.src.shap_explainer import generate_shap_explanation
from ml.explainability.src.lime_explainer import generate_lime_explanation

# Neutral defaults for the 14 fields the current questionnaire doesn't collect.
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
    """Maps the 10 frontend fields into the model's field names, then fills
    the remaining 14 fields — using a real value from questionnaire_answers
    if the frontend ever sends one under the model's own field name (see
    DEFAULT_FIELDS keys above), falling back to the neutral default only
    when no real value is present. This means once the frontend starts
    collecting these fields, they'll be used automatically with no backend
    change required — as long as the frontend sends them under these exact
    snake_case names (e.g. "mutual_funds", "equity_market"), the same way
    it already does for the existing 10 dataset-matched fields.
    """
    mapped = {
        "gender": questionnaire_answers["gender"],
        "age": questionnaire_answers["age"],
        "investment_avenues": questionnaire_answers["Investment_Avenues"],
        "stock_market": questionnaire_answers["Stock_Marktet"],
        "factor": questionnaire_answers["Factor"],
        "objective": questionnaire_answers["Objective"],
        "duration": questionnaire_answers["Duration"],
        "invest_monitor": questionnaire_answers["Invest_Monitor"],
        "expect": questionnaire_answers["Expect"],
        "avenue": questionnaire_answers["Avenue"],
    }

    for field, default_value in DEFAULT_FIELDS.items():
        mapped[field] = questionnaire_answers.get(field, default_value)

    return mapped

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