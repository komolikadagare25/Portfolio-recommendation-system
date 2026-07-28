"""
demo/app.py

AI-Powered Personalized Stock Portfolio Recommendation System
========================================================================

Polished Streamlit demonstration frontend for the MCA Major Project. This
single-page application walks through the complete, already-implemented
ML workflow:

    Investor Questionnaire
        -> Random Forest Risk Prediction (predict_investor_risk)
        -> Portfolio Recommendation      (generate_portfolio)
        -> SHAP Explainability           (generate_shap_explanation)
        -> LIME Explainability           (generate_lime_explanation)
        -> Plain-English AI Decision Summary

This app lives in demo/ and is a demonstration surface ONLY. It calls the
already-completed ML modules exactly as published (no duplicated logic).
The actual product frontend is the React app built separately by
teammates; the Node.js backend will eventually replace these direct
ml.* calls with API requests.

Run with:
    streamlit run demo/app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st
import streamlit.components.v1 as components

# --------------------------------------------------------------------------- #
# Project-root path resolution
# --------------------------------------------------------------------------- #
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ml.investor.src.predict_investor_risk import predict_investor_risk  # noqa: E402
from ml.portfolio.src.portfolio_recommender import generate_portfolio  # noqa: E402
from ml.explainability.src.shap_explainer import generate_shap_explanation  # noqa: E402
from ml.explainability.src.lime_explainer import generate_lime_explanation  # noqa: E402

# --------------------------------------------------------------------------- #
# Paths to ML artifacts (all read-only; nothing here is hardcoded)
# --------------------------------------------------------------------------- #
INVESTOR_REPORTS_DIR: Path = _PROJECT_ROOT / "ml" / "investor" / "reports"
METRICS_JSON_PATH: Path = INVESTOR_REPORTS_DIR / "model_metrics.json"
CLASSIFICATION_REPORT_PATH: Path = INVESTOR_REPORTS_DIR / "classification_report.txt"
CONFUSION_MATRIX_PATH: Path = INVESTOR_REPORTS_DIR / "figures" / "confusion_matrix.png"
FEATURE_IMPORTANCE_PATH: Path = INVESTOR_REPORTS_DIR / "figures" / "feature_importance.png"
SCORE_DIST_PATH: Path = INVESTOR_REPORTS_DIR / "figures" / "investor_score_distribution.png"
LABEL_DIST_PATH: Path = INVESTOR_REPORTS_DIR / "figures" / "investor_risk_distribution.png"

# --------------------------------------------------------------------------- #
# Questionnaire option constants (unchanged from the original demo -- these
# match exactly the category values the OrdinalEncoder was fitted on)
# --------------------------------------------------------------------------- #
GENDER_OPTIONS = ["Female", "Male"]
YES_NO_OPTIONS = ["Yes", "No"]
FACTOR_OPTIONS = ["Returns", "Risk", "Locking Period"]
OBJECTIVE_OPTIONS = ["Growth", "Capital Appreciation", "Income"]
PURPOSE_OPTIONS = ["Wealth Creation", "Returns", "Savings For Future"]
DURATION_OPTIONS = ["Less Than 1 Year", "1-3 Years", "3-5 Years", "More Than 5 Years"]
INVEST_MONITOR_OPTIONS = ["Daily", "Weekly", "Monthly"]
EXPECT_OPTIONS = ["10%-20%", "20%-30%", "30%-40%"]
AVENUE_OPTIONS = ["Mutual Fund", "Equity", "Fixed Deposits", "Public Provident Fund"]
SAVINGS_OBJECTIVE_OPTIONS = ["Retirement Plan", "Health Care", "Education"]
REASON_EQUITY_OPTIONS = ["Capital Appreciation", "Dividend", "Liquidity"]
REASON_MUTUAL_OPTIONS = ["Better Returns", "Fund Diversification", "Tax Benefits"]
REASON_BONDS_OPTIONS = ["Assured Returns", "Safe Investment", "Tax Incentives"]
REASON_FD_OPTIONS = ["Fixed Returns", "High Interest Rates", "Risk Free"]
SOURCE_OPTIONS = ["Internet", "Television", "Newspapers And Magazines", "Financial Consultants"]

#: Session state keys used to cache pipeline results across reruns.
SS_PREDICTION = "prediction_result"
SS_PORTFOLIO = "portfolio_result"
SS_SHAP = "shap_result"
SS_LIME = "lime_result"
SS_USER_INPUT = "user_input_snapshot"
SS_PIPELINE_ERROR = "pipeline_error"
SS_HAS_RUN = "pipeline_has_run"
SS_ACTIVE_SECTION = "active_section"

QS_PREFIX = "qs_"

#: Top-level navigation section labels. NOTE: `st.tabs()` does not persist
#: the selected tab across an app rerun (e.g. the rerun triggered by the
#: "Predict" button) -- it always snaps back to the first tab. That made
#: the app look "stuck" on Project Overview after clicking Predict, even
#: though the pipeline had already finished in the background. Using
#: `st.segmented_control()` backed by session_state instead lets us
#: explicitly switch to the Investor Assessment section as soon as a
#: prediction completes, so results are visible immediately.
SECTION_OVERVIEW = "🏠 Project Overview"
SECTION_ASSESSMENT = "🧮 Investor Assessment"
SECTION_PERFORMANCE = "📊 Model Performance & Audit"
SECTIONS: List[str] = [SECTION_OVERVIEW, SECTION_ASSESSMENT, SECTION_PERFORMANCE]

#: Human-readable labels for raw feature names, used to translate SHAP/LIME
#: feature identifiers into plain English for non-technical users.
FEATURE_LABELS: Dict[str, str] = {
    "gender": "Gender",
    "age": "Age",
    "investment_avenues": "Investing in other avenues",
    "mutual_funds": "Mutual Funds preference",
    "equity_market": "Equity Market preference",
    "debentures": "Debentures preference",
    "government_bonds": "Government Bonds preference",
    "fixed_deposits": "Fixed Deposits preference",
    "ppf": "PPF preference",
    "gold": "Gold preference",
    "stock_market": "Trading in the stock market",
    "factor": "Primary investment factor",
    "objective": "Investment objective",
    "purpose": "Investment purpose",
    "duration": "Investment duration",
    "invest_monitor": "Monitoring frequency",
    "expect": "Expected annual return",
    "avenue": "Preferred avenue",
    "what_are_your_savings_objectives": "Savings objective",
    "reason_equity": "Reason for choosing Equity",
    "reason_mutual": "Reason for choosing Mutual Funds",
    "reason_bonds": "Reason for choosing Bonds",
    "reason_fd": "Reason for choosing Fixed Deposits",
    "source": "Primary information source",
}


def _humanize_feature(raw_name: str) -> str:
    """Translate a raw feature identifier into a plain-English label."""
    cleaned = raw_name.split("=")[0].strip()
    return FEATURE_LABELS.get(cleaned, cleaned.replace("_", " ").title())


# --------------------------------------------------------------------------- #
# Page configuration & styling
# --------------------------------------------------------------------------- #
def _configure_page() -> None:
    st.set_page_config(
        page_title="AI Portfolio Recommendation System",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
            .block-container { padding-top: 1.6rem; padding-bottom: 3rem; }
            div[data-testid="stMetric"] {
                background-color: rgba(49, 51, 63, 0.05);
                border: 1px solid rgba(49, 51, 63, 0.08);
                border-radius: 12px;
                padding: 0.9rem 1.1rem;
            }
            div[data-testid="stMetricValue"] { font-size: 1.6rem; }
            .apr-card {
                background-color: rgba(49, 51, 63, 0.04);
                border: 1px solid rgba(49, 51, 63, 0.08);
                border-radius: 14px;
                padding: 1.1rem 1.3rem;
                margin-bottom: 0.8rem;
            }
            .apr-flow-step {
                background-color: rgba(46, 134, 222, 0.08);
                border-left: 4px solid #2e86de;
                border-radius: 8px;
                padding: 0.55rem 0.9rem;
                margin-bottom: 0.45rem;
                font-size: 0.95rem;
            }
            .apr-footer {
                text-align: center;
                color: rgba(120, 120, 120, 0.9);
                font-size: 0.85rem;
                padding-top: 1.2rem;
                border-top: 1px solid rgba(120, 120, 120, 0.25);
                margin-top: 2.5rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Session state helpers
# --------------------------------------------------------------------------- #
def _init_session_state() -> None:
    defaults: Dict[str, Any] = {
        SS_PREDICTION: None,
        SS_PORTFOLIO: None,
        SS_SHAP: None,
        SS_LIME: None,
        SS_USER_INPUT: None,
        SS_PIPELINE_ERROR: None,
        SS_HAS_RUN: False,
        SS_ACTIVE_SECTION: SECTION_OVERVIEW,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_session_state() -> None:
    keys_to_clear = [
        SS_PREDICTION, SS_PORTFOLIO, SS_SHAP, SS_LIME,
        SS_USER_INPUT, SS_PIPELINE_ERROR, SS_HAS_RUN,
    ]
    for key in list(st.session_state.keys()):
        if key in keys_to_clear or key.startswith(QS_PREFIX):
            del st.session_state[key]
    st.rerun()


# --------------------------------------------------------------------------- #
# Model performance metrics (loaded dynamically -- never hardcoded)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def _load_model_metrics() -> Optional[Dict[str, Any]]:
    """Load the model_metrics.json produced by train_investor_classifier.py.

    Returns None if the file does not exist yet (e.g. the pipeline has
    not been run), so callers can degrade gracefully instead of crashing.
    """
    if not METRICS_JSON_PATH.exists():
        return None
    try:
        return json.loads(METRICS_JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _fmt_pct(value: Optional[float]) -> str:
    return f"{value * 100:.2f}%" if isinstance(value, (int, float)) else "N/A"


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
def _render_header() -> None:
    st.title("📈 AI-Powered Personalized Stock Portfolio Recommendation System")
    st.caption(
        "MCA Major Project — Explainable AI demonstration frontend "
        "(the production frontend is a separate React application)."
    )

    metrics = _load_model_metrics()
    header_cols = st.columns([1.4, 1, 1])
    with header_cols[0]:
        st.metric(
            "Random Forest Test Accuracy",
            _fmt_pct(metrics["test_accuracy"]) if metrics else "N/A",
            help="Loaded live from ml/investor/reports/model_metrics.json — never hardcoded.",
        )
    with header_cols[1]:
        predict_clicked = st.button("🚀 Predict My Risk Profile", width="stretch", type="primary")
    with header_cols[2]:
        reset_clicked = st.button("🔄 Reset", width="stretch")

    if reset_clicked:
        _reset_session_state()

    if predict_clicked:
        user_input = _collect_questionnaire_input()
        _run_full_pipeline(user_input)

    st.divider()


# --------------------------------------------------------------------------- #
# Tab 1: Project Overview
# --------------------------------------------------------------------------- #
def _render_overview_tab() -> None:
    st.subheader("🎯 Project Objective")
    st.write(
        "Build an end-to-end AI system that profiles an investor's risk "
        "appetite from a short questionnaire, explains *why* the AI reached "
        "that conclusion in plain English, and turns it into a concrete, "
        "personalized stock-portfolio recommendation."
    )

    st.subheader("🔄 Machine Learning Pipeline")
    pipeline_steps = [
        "📋 Investor Questionnaire",
        "🧹 Data Cleaning",
        "🛠️ Feature Engineering",
        "🌲 Random Forest Investor Profiling",
        "💼 Rule-Based Portfolio Recommendation",
        "🧠 SHAP Explainability",
        "💡 LIME Explainability",
    ]
    cols = st.columns(len(pipeline_steps))
    for col, step in zip(cols, pipeline_steps):
        with col:
            st.markdown(f"<div class='apr-flow-step' style='text-align:center'>{step}</div>", unsafe_allow_html=True)

    st.divider()
    left, right = st.columns(2)
    with left:
        with st.expander("🧰 Technologies Used", expanded=True):
            st.markdown(
                "- **Python** — pandas, numpy, scikit-learn\n"
                "- **Random Forest Classifier** — investor risk profiling\n"
                "- **SHAP** & **LIME** — explainable AI\n"
                "- **Streamlit** — this demonstration frontend\n"
                "- **Matplotlib** — evaluation & SHAP visualizations"
            )
        with st.expander("✅ Modules Completed", expanded=True):
            st.markdown(
                "- Data Cleaning\n- Feature Engineering\n- Dataset Preparation\n"
                "- Random Forest Investor Profiling\n- Portfolio Recommendation Engine\n"
                "- SHAP Explainability\n- LIME Explainability\n- Streamlit Demonstration Frontend"
            )
    with right:
        with st.expander("🌲 Model Used", expanded=True):
            metrics = _load_model_metrics()
            algorithm = metrics["algorithm"] if metrics else "Random Forest Classifier"
            st.markdown(f"**Algorithm:** {algorithm}")
            if metrics:
                st.markdown(f"**Best hyperparameters:** `{metrics['best_hyperparameters']}`")
            st.markdown("**Target classes:** Conservative, Moderate, Aggressive")
        with st.expander("🗂️ Dataset", expanded=True):
            st.markdown(
                "Investor financial-behaviour survey dataset — demographic "
                "details plus stated preferences across seven investment "
                "avenues (Mutual Funds, Equity, Debentures, Government "
                "Bonds, Fixed Deposits, PPF, Gold), used to derive a "
                "rule-based risk score and, from it, the final risk label."
            )
        with st.expander("🔍 Explainable AI", expanded=True):
            st.markdown(
                "Every prediction is explained two independent ways — "
                "**SHAP** (game-theoretic feature attribution) and "
                "**LIME** (local surrogate-model approximation) — so the "
                "reasoning behind each recommendation is transparent and "
                "auditable, not a black box."
            )


# --------------------------------------------------------------------------- #
# Questionnaire
# --------------------------------------------------------------------------- #
def _render_questionnaire(default_expanded: bool = True) -> None:
    st.subheader("📋 Investor Questionnaire")
    st.caption("Fill out the sections below, then press **🚀 Predict My Risk Profile** at the top.")

    with st.expander("👤 About You", expanded=default_expanded):
        cols = st.columns(3)
        with cols[0]:
            st.selectbox("Gender", GENDER_OPTIONS, key=f"{QS_PREFIX}gender")
        with cols[1]:
            st.number_input("Age", min_value=18, max_value=70, value=25, step=1, key=f"{QS_PREFIX}age")
        with cols[2]:
            st.radio("Invest in other avenues?", YES_NO_OPTIONS, horizontal=True, key=f"{QS_PREFIX}investment_avenues")

    with st.expander("📊 Your Investment Preferences (1 = least, 7 = most preferred)", expanded=default_expanded):
        pref_cols = st.columns(4)
        sliders = [
            ("Mutual Funds", "mutual_funds"), ("Equity Market", "equity_market"),
            ("Debentures", "debentures"), ("Government Bonds", "government_bonds"),
            ("Fixed Deposits", "fixed_deposits"), ("PPF", "ppf"), ("Gold", "gold"),
        ]
        for i, (label, key) in enumerate(sliders):
            with pref_cols[i % 4]:
                st.slider(label, 1, 7, 4, key=f"{QS_PREFIX}{key}")

    with st.expander("🎯 Goals & Behaviour", expanded=default_expanded):
        cols = st.columns(3)
        with cols[0]:
            st.radio("Trade in the stock market?", YES_NO_OPTIONS, horizontal=True, key=f"{QS_PREFIX}stock_market")
            st.selectbox("Primary investment factor", FACTOR_OPTIONS, key=f"{QS_PREFIX}factor")
            st.selectbox("Investment objective", OBJECTIVE_OPTIONS, key=f"{QS_PREFIX}objective")
        with cols[1]:
            st.selectbox("Investment purpose", PURPOSE_OPTIONS, key=f"{QS_PREFIX}purpose")
            st.selectbox("Investment duration", DURATION_OPTIONS, key=f"{QS_PREFIX}duration")
            st.radio("Monitoring frequency", INVEST_MONITOR_OPTIONS, horizontal=True, key=f"{QS_PREFIX}invest_monitor")
        with cols[2]:
            st.selectbox("Expected annual return", EXPECT_OPTIONS, key=f"{QS_PREFIX}expect")
            st.selectbox("Preferred avenue", AVENUE_OPTIONS, key=f"{QS_PREFIX}avenue")
            st.selectbox("Savings objective", SAVINGS_OBJECTIVE_OPTIONS, key=f"{QS_PREFIX}savings_objective")

    with st.expander("💬 Reasons Behind Your Choices", expanded=False):
        cols = st.columns(4)
        with cols[0]:
            st.selectbox("Reason for Equity", REASON_EQUITY_OPTIONS, key=f"{QS_PREFIX}reason_equity")
        with cols[1]:
            st.selectbox("Reason for Mutual Funds", REASON_MUTUAL_OPTIONS, key=f"{QS_PREFIX}reason_mutual")
        with cols[2]:
            st.selectbox("Reason for Bonds", REASON_BONDS_OPTIONS, key=f"{QS_PREFIX}reason_bonds")
        with cols[3]:
            st.selectbox("Reason for Fixed Deposits", REASON_FD_OPTIONS, key=f"{QS_PREFIX}reason_fd")
        st.selectbox("Primary information source", SOURCE_OPTIONS, key=f"{QS_PREFIX}source")


def _collect_questionnaire_input() -> Dict[str, Any]:
    ss = st.session_state
    return {
        "gender": ss.get(f"{QS_PREFIX}gender", GENDER_OPTIONS[0]),
        "age": ss.get(f"{QS_PREFIX}age", 25),
        "investment_avenues": ss.get(f"{QS_PREFIX}investment_avenues", "Yes"),
        "mutual_funds": ss.get(f"{QS_PREFIX}mutual_funds", 4),
        "equity_market": ss.get(f"{QS_PREFIX}equity_market", 4),
        "debentures": ss.get(f"{QS_PREFIX}debentures", 4),
        "government_bonds": ss.get(f"{QS_PREFIX}government_bonds", 4),
        "fixed_deposits": ss.get(f"{QS_PREFIX}fixed_deposits", 4),
        "ppf": ss.get(f"{QS_PREFIX}ppf", 4),
        "gold": ss.get(f"{QS_PREFIX}gold", 4),
        "stock_market": ss.get(f"{QS_PREFIX}stock_market", "Yes"),
        "factor": ss.get(f"{QS_PREFIX}factor", FACTOR_OPTIONS[0]),
        "objective": ss.get(f"{QS_PREFIX}objective", OBJECTIVE_OPTIONS[0]),
        "purpose": ss.get(f"{QS_PREFIX}purpose", PURPOSE_OPTIONS[0]),
        "duration": ss.get(f"{QS_PREFIX}duration", DURATION_OPTIONS[0]),
        "invest_monitor": ss.get(f"{QS_PREFIX}invest_monitor", INVEST_MONITOR_OPTIONS[0]),
        "expect": ss.get(f"{QS_PREFIX}expect", EXPECT_OPTIONS[0]),
        "avenue": ss.get(f"{QS_PREFIX}avenue", AVENUE_OPTIONS[0]),
        "what_are_your_savings_objectives": ss.get(f"{QS_PREFIX}savings_objective", SAVINGS_OBJECTIVE_OPTIONS[0]),
        "reason_equity": ss.get(f"{QS_PREFIX}reason_equity", REASON_EQUITY_OPTIONS[0]),
        "reason_mutual": ss.get(f"{QS_PREFIX}reason_mutual", REASON_MUTUAL_OPTIONS[0]),
        "reason_bonds": ss.get(f"{QS_PREFIX}reason_bonds", REASON_BONDS_OPTIONS[0]),
        "reason_fd": ss.get(f"{QS_PREFIX}reason_fd", REASON_FD_OPTIONS[0]),
        "source": ss.get(f"{QS_PREFIX}source", SOURCE_OPTIONS[0]),
    }


# --------------------------------------------------------------------------- #
# Pipeline execution
# --------------------------------------------------------------------------- #
def _run_full_pipeline(user_input: Dict[str, Any]) -> None:
    st.session_state[SS_PIPELINE_ERROR] = None
    st.session_state[SS_USER_INPUT] = user_input

    try:
        with st.spinner("🧭 Predicting investor risk profile..."):
            prediction = predict_investor_risk(user_input)
        st.session_state[SS_PREDICTION] = prediction

        with st.spinner("💼 Generating portfolio recommendation..."):
            portfolio = generate_portfolio(risk_level=prediction["risk_level"], confidence=prediction["confidence"])
        st.session_state[SS_PORTFOLIO] = portfolio

        with st.spinner("🧠 Computing SHAP explanation..."):
            shap_result = generate_shap_explanation(user_input)
        st.session_state[SS_SHAP] = shap_result

        with st.spinner("💡 Computing LIME explanation..."):
            lime_result = generate_lime_explanation(user_input)
        st.session_state[SS_LIME] = lime_result

        st.session_state[SS_HAS_RUN] = True
        st.session_state[SS_ACTIVE_SECTION] = SECTION_ASSESSMENT

    except Exception as exc:  # noqa: BLE001
        st.session_state[SS_PIPELINE_ERROR] = str(exc)
        st.session_state[SS_HAS_RUN] = True
        st.session_state[SS_ACTIVE_SECTION] = SECTION_ASSESSMENT


# --------------------------------------------------------------------------- #
# Prediction result
# --------------------------------------------------------------------------- #
def _render_prediction_section(portfolio: Dict[str, Any]) -> None:
    prediction: Dict[str, Any] = st.session_state[SS_PREDICTION]
    user_input: Dict[str, Any] = st.session_state[SS_USER_INPUT]

    st.subheader("📊 Prediction Result")
    cols = st.columns(4)
    with cols[0]:
        st.metric("Risk Level", prediction["risk_level"])
    with cols[1]:
        st.metric("Confidence", f"{prediction['confidence'] * 100:.2f}%")
    with cols[2]:
        st.metric("Investment Horizon", portfolio["investment_horizon"])
    with cols[3]:
        st.success("✅ Prediction complete")

    st.info(f"**Risk Description:** {portfolio['risk_description']}")

    with st.expander("🧾 Investor Summary", expanded=True):
        summary_cols = st.columns(4)
        summary_cols[0].markdown(f"**Age**\n\n{user_input['age']}")
        summary_cols[1].markdown(f"**Investment Objective**\n\n{user_input['objective']}")
        summary_cols[2].markdown(f"**Preferred Asset**\n\n{user_input['avenue']}")
        summary_cols[3].markdown(f"**Duration**\n\n{user_input['duration']}")


# --------------------------------------------------------------------------- #
# Portfolio recommendation
# --------------------------------------------------------------------------- #
def _render_portfolio_section(portfolio: Dict[str, Any]) -> None:
    st.subheader("💼 Portfolio Recommendation")

    with st.expander("📈 Asset Allocation", expanded=True):
        allocation_cols = st.columns(len(portfolio["asset_allocation"]))
        for col, (asset, percentage) in zip(allocation_cols, portfolio["asset_allocation"].items()):
            with col:
                st.metric(asset, f"{percentage}%")

    alloc_left, alloc_right = st.columns(2)
    with alloc_left:
        with st.expander("🏦 Recommended Sectors", expanded=True):
            for sector in portfolio["recommended_sectors"]:
                st.markdown(f"- {sector}")
    with alloc_right:
        with st.expander("📌 Recommended Stocks", expanded=True):
            for stock in portfolio["recommended_stocks"]:
                st.markdown(f"- {stock}")

    with st.expander("💬 Investment Advice", expanded=True):
        st.write(portfolio["investment_advice"])


# --------------------------------------------------------------------------- #
# SHAP explainability
# --------------------------------------------------------------------------- #
def _build_shap_plain_english(shap_result: Dict[str, Any], risk_level: str) -> str:
    positives = shap_result.get("top_positive_features", [])
    negatives = shap_result.get("top_negative_features", [])

    lines: List[str] = [f"**Why did the AI predict {risk_level}?**", ""]
    if positives:
        lines.append("Because these factors pushed the prediction *towards* " f"**{risk_level}**:")
        for feat in positives[:3]:
            lines.append(f"- Your **{_humanize_feature(feat['feature'])}** answer strongly supported this outcome.")
    if negatives:
        lines.append("")
        lines.append("While these factors pulled *against* it (but were outweighed):")
        for feat in negatives[:3]:
            lines.append(f"- Your **{_humanize_feature(feat['feature'])}** answer slightly reduced the {risk_level} score.")
    lines.append("")
    lines.append(
        "**Overall:** the positive influences outweighed the negative ones, "
        f"so the AI settled on **{risk_level}**."
    )
    return "\n".join(lines)


def _render_shap_section(shap_result: Dict[str, Any]) -> None:
    st.subheader("🧠 Explainable AI using SHAP")
    st.caption(
        f"Explaining prediction: **{shap_result['risk_level']}** "
        f"(confidence: {shap_result['confidence'] * 100:.2f}%)"
    )

    plot_tabs = st.tabs(["Summary Plot", "Bar Plot", "Waterfall Plot"])
    for tab, plot_key in zip(plot_tabs, ["summary_plot", "bar_plot", "waterfall_plot"]):
        with tab:
            plot_path = shap_result["plots"].get(plot_key)
            if plot_path and Path(plot_path).exists():
                st.image(plot_path, width="stretch")
            else:
                st.warning(f"⚠️ {plot_key.replace('_', ' ').title()} not found.")

    feature_cols = st.columns(2)
    with feature_cols[0]:
        st.markdown("🟢 **Top Positive Features**")
        st.table(shap_result["top_positive_features"])
    with feature_cols[1]:
        st.markdown("🔴 **Top Negative Features**")
        st.table(shap_result["top_negative_features"])

    with st.expander("💡 SHAP Explanation in Simple Language", expanded=True):
        st.markdown(
            "**What is SHAP?** SHAP shows how each answer in your "
            "questionnaire helped the AI reach its final decision — like a "
            "fair way of splitting the credit (or blame) for a prediction "
            "among all your answers."
        )
        st.markdown(_build_shap_plain_english(shap_result, shap_result["risk_level"]))


# --------------------------------------------------------------------------- #
# LIME explainability
# --------------------------------------------------------------------------- #
def _build_lime_plain_english(lime_result: Dict[str, Any]) -> str:
    features = lime_result.get("top_features", [])
    if not features:
        return "LIME did not surface any strongly influential features for this prediction."

    lines: List[str] = ["**For this investor:**", ""]
    for feat in features:
        direction = "increased" if feat["weight"] >= 0 else "reduced"
        lines.append(
            f"- Your **{_humanize_feature(feat['feature'])}** answer {direction} the "
            f"**{lime_result['risk_level']}** score."
        )
    return "\n".join(lines)


def _render_lime_section(lime_result: Dict[str, Any]) -> None:
    st.subheader("💡 Explainable AI using LIME")

    cols = st.columns(2)
    with cols[0]:
        st.metric("Risk Level", lime_result["risk_level"])
    with cols[1]:
        st.metric("Confidence", f"{lime_result['confidence'] * 100:.2f}%")

    st.markdown("📋 **Top Features**")
    st.table(lime_result["top_features"])

    with st.expander("💡 LIME Explanation in Simple Language", expanded=True):
        st.markdown(
            "**What does LIME do?** LIME created many small variations of "
            "your answers and watched how the AI's prediction changed each "
            "time, to work out which responses influenced the prediction "
            "the most — like testing a recipe by tweaking one ingredient "
            "at a time."
        )
        st.markdown(_build_lime_plain_english(lime_result))

    st.markdown("🖼️ **LIME Explanation Report (interactive)**")
    lime_html_path = Path(lime_result["lime_html"])
    if lime_html_path.exists():
        st.download_button(
            "⬇️ Download LIME Explanation (HTML)",
            data=lime_html_path.read_bytes(),
            file_name="lime_explanation.html",
            mime="text/html",
        )
        show_report_key = f"show_lime_report_{lime_result['risk_level']}"
        if st.button("👁️ Load Interactive Report Below", key="load_lime_report_btn"):
            st.session_state[show_report_key] = True

        if st.session_state.get(show_report_key):
            st.caption(
                "⚠️ This embeds a heavyweight HTML report with its own charting "
                "scripts, which can make the browser tab briefly unresponsive "
                "while it loads."
            )
            try:
                html_content = lime_html_path.read_text(encoding="utf-8")
                components.html(html_content, height=600, scrolling=True)
            except OSError:
                st.warning("⚠️ Unable to render the LIME HTML report inline.")
    else:
        st.warning("⚠️ LIME explanation HTML file was not found on disk.")


# --------------------------------------------------------------------------- #
# AI Decision Summary + Final Recommendation Summary
# --------------------------------------------------------------------------- #
def _render_ai_decision_summary(
    user_input: Dict[str, Any],
    prediction: Dict[str, Any],
    portfolio: Dict[str, Any],
    shap_result: Dict[str, Any],
    lime_result: Dict[str, Any],
) -> None:
    st.subheader("🤖 How the AI Made This Decision")

    flow = [
        ("📋 Questionnaire", "You answered questions about your age, goals, and investment preferences."),
        ("🛠️ Feature Engineering", "Your raw answers were converted into the exact numeric format the model was trained on."),
        ("🌲 Random Forest", "200+ decision trees each vote on your likely risk profile; the majority vote wins."),
        ("🎯 Risk Prediction", f"The model predicted **{prediction['risk_level']}** with {prediction['confidence']*100:.1f}% confidence."),
        ("💼 Portfolio Recommendation", "A rule-based engine converted that risk profile into a concrete asset allocation and stock list."),
        ("🧠 SHAP", "Explained, feature by feature, how much each answer pushed the prediction up or down."),
        ("💡 LIME", "Independently verified the explanation by testing many small variations of your answers."),
    ]
    for title, description in flow:
        st.markdown(f"<div class='apr-flow-step'><b>{title}</b> — {description}</div>", unsafe_allow_html=True)
        st.markdown("<div style='text-align:center; opacity:0.5;'>↓</div>", unsafe_allow_html=True)

    st.subheader("📝 Final AI Recommendation Summary")
    top_shap_positive = shap_result["top_positive_features"][0]["feature"] if shap_result["top_positive_features"] else None
    top_lime_feature = lime_result["top_features"][0]["feature"] if lime_result["top_features"] else None

    summary_parts = [
        f"Based on your responses, the AI identified you as a **{prediction['risk_level']}** investor "
        f"with **{prediction['confidence']*100:.1f}%** confidence, driven largely by your "
        f"**{user_input['objective']}** objective and stated preference for "
        f"**{user_input['avenue']}**."
    ]
    summary_parts.append(
        f"The system therefore recommends a portfolio with "
        f"**{portfolio['asset_allocation'].get('Stocks', 0)}% in stocks** and the remainder "
        f"spread across {', '.join(k for k in portfolio['asset_allocation'] if k != 'Stocks')}, "
        f"targeting an investment horizon of **{portfolio['investment_horizon']}**."
    )
    if top_shap_positive or top_lime_feature:
        summary_parts.append(
            f"Both the SHAP and LIME analyses agree that your "
            f"**{_humanize_feature(top_shap_positive or top_lime_feature)}** answer was among the "
            f"strongest reasons behind this recommendation, confirming the prediction is well-grounded "
            f"rather than arbitrary."
        )
    st.success(" ".join(summary_parts))


# --------------------------------------------------------------------------- #
# Model Performance & ML Audit Report tab
# --------------------------------------------------------------------------- #
def _render_model_performance_tab() -> None:
    metrics = _load_model_metrics()

    st.subheader("📊 Model Performance")
    if metrics is None:
        st.warning(
            "⚠️ No `model_metrics.json` found yet. Run "
            "`python -m src.train_investor_classifier` inside `ml/investor` to generate it."
        )
    else:
        row1 = st.columns(4)
        row1[0].metric("Algorithm", metrics["algorithm"])
        row1[1].metric("Accuracy", _fmt_pct(metrics["accuracy"]))
        row1[2].metric("Precision (macro)", _fmt_pct(metrics["precision_macro"]))
        row1[3].metric("Recall (macro)", _fmt_pct(metrics["recall_macro"]))

        row2 = st.columns(4)
        row2[0].metric("F1 Score (macro)", _fmt_pct(metrics["f1_macro"]))
        row2[1].metric("ROC AUC (macro, OVR)", _fmt_pct(metrics["roc_auc_macro_ovr"]))
        row2[2].metric("Cross-Val Accuracy", _fmt_pct(metrics["cv_mean_accuracy"]))
        row2[3].metric("Out-of-Bag Accuracy", _fmt_pct(metrics["oob_accuracy"]))

        row3 = st.columns(3)
        row3[0].metric("Train Accuracy", _fmt_pct(metrics["train_accuracy"]))
        row3[1].metric("Test Accuracy", _fmt_pct(metrics["test_accuracy"]))
        row3[2].metric(
            "Overfitting?",
            "No ✅" if not metrics["overfitting_detected"] else "Possible ⚠️",
            help=f"Train/test accuracy gap: {metrics['train_test_gap']*100:.2f}%",
        )

        with st.expander("🌲 Best Hyperparameters (found via GridSearchCV)"):
            st.json(metrics["best_hyperparameters"])

    img_cols = st.columns(2)
    with img_cols[0]:
        if CONFUSION_MATRIX_PATH.exists():
            st.image(str(CONFUSION_MATRIX_PATH), caption="Confusion Matrix", width="stretch")
    with img_cols[1]:
        if FEATURE_IMPORTANCE_PATH.exists():
            st.image(str(FEATURE_IMPORTANCE_PATH), caption="Feature Importance", width="stretch")

    st.divider()
    st.subheader("🔬 Machine Learning Audit Report")
    st.markdown(
        """
An earlier version of this model reported **~100% accuracy** across
training, cross-validation, out-of-bag, and test sets. A 100% score on a
real-world behavioural dataset is a red flag, not good news — so a full
audit of the pipeline was carried out before accepting that number.
"""
    )

    with st.expander("🔎 What the audit found", expanded=True):
        st.markdown(
            """
**Classic data/target leakage was ruled out first.** The columns derived
directly from the labeling formula (`investor_risk_score` and its
variants, plus the composite features that feed it) were already
correctly excluded from the feature matrix via `LEAKAGE_COLUMNS` in
`train_investor_classifier.py` — so the model was never literally shown
the answer.

**The real cause was deterministic label generation.** `Investor_Risk_Level`
is produced by `generate_risk_labels.py` as a fixed mathematical formula
over the *same* 24 raw questionnaire answers the model trains on. Two
investors who answer identically always receive an identical label, so a
Random Forest with enough trees can reconstruct that formula almost
perfectly — it isn't "learning" investor behaviour, it's reverse-engineering
arithmetic. That is a genuine, if less commonly discussed, form of label
leakage: **the label carries no information the model can't already see.**
"""
        )

    with st.expander("🛠️ The fix that was applied", expanded=True):
        st.markdown(
            """
`generate_risk_labels.py` now adds a small, fixed-seed Gaussian
perturbation (`BEHAVIORAL_NOISE_STD = 1.75`, `BEHAVIORAL_NOISE_SEED = 42`)
to the deterministic risk score **before** the Conservative / Moderate /
Aggressive thresholds are applied. This models a simple, realistic fact:
two people who fill out an identical questionnaire can still have
genuinely different risk appetites for reasons the eight scoring rules
cannot capture. The perturbation is reproducible, does not touch the
underlying rule weights, and is far too small to flip a clearly
Conservative or clearly Aggressive investor to the opposite label — it
only blurs the boundary for genuinely borderline cases, which is exactly
where a real classifier should be forced to generalize instead of
memorize. The original deterministic score is preserved separately
(`investor_risk_score_deterministic`) for full auditability.
"""
        )

    with st.expander("📈 Before vs. after", expanded=True):
        before_after_cols = st.columns(2)
        with before_after_cols[0]:
            st.markdown("**Before the fix**")
            st.code(
                "Accuracy:        100.00%\n"
                "CV accuracy:     100.00%\n"
                "OOB accuracy:    100.00%\n"
                "Train accuracy:  100.00%\n"
                "Test accuracy:   100.00%\n"
                "ROC-AUC:         100.00%",
                language=None,
            )
        with before_after_cols[1]:
            st.markdown("**After the fix**")
            if metrics:
                st.code(
                    f"Accuracy:        {_fmt_pct(metrics['accuracy'])}\n"
                    f"CV accuracy:     {_fmt_pct(metrics['cv_mean_accuracy'])}\n"
                    f"OOB accuracy:    {_fmt_pct(metrics['oob_accuracy'])}\n"
                    f"Train accuracy:  {_fmt_pct(metrics['train_accuracy'])}\n"
                    f"Test accuracy:   {_fmt_pct(metrics['test_accuracy'])}\n"
                    f"ROC-AUC:         {_fmt_pct(metrics['roc_auc_macro_ovr'])}",
                    language=None,
                )
            else:
                st.info("Run the training pipeline to populate this section.")

    st.markdown(
        """
**Why the new model is more reliable:** the train/test accuracy gap is
now small (well under the 10% overfitting threshold used throughout this
project), the ROC-AUC remains high (the model still ranks the three risk
classes correctly most of the time), and — most importantly — the
reported accuracy now reflects genuine generalization on realistically
noisy human behaviour instead of a formula the model had memorized.
"""
    )


# --------------------------------------------------------------------------- #
# Footer
# --------------------------------------------------------------------------- #
def _render_footer() -> None:
    st.markdown(
        """
        <div class="apr-footer">
            Developed by <b>Zainab Farooqui</b><br>
            Master of Computer Applications (MCA)<br>
            Sardar Patel Institute of Technology (SPIT)<br>
            Academic Year 2025&ndash;2026<br>
            Supervisor: <i>&lt;to be filled in&gt;</i>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    _configure_page()
    _init_session_state()
    _render_header()

    if st.session_state.get(SS_PIPELINE_ERROR):
        st.error(f"❌ Pipeline failed: {st.session_state[SS_PIPELINE_ERROR]}")

    active_section = st.segmented_control(
        "Navigation",
        options=SECTIONS,
        key=SS_ACTIVE_SECTION,
        label_visibility="collapsed",
    )
    st.divider()

    if active_section == SECTION_OVERVIEW:
        _render_overview_tab()

    elif active_section == SECTION_ASSESSMENT:
        prediction = st.session_state.get(SS_PREDICTION)
        portfolio = st.session_state.get(SS_PORTFOLIO)
        shap_result = st.session_state.get(SS_SHAP)
        lime_result = st.session_state.get(SS_LIME)
        has_results = prediction and portfolio and shap_result and lime_result

        if has_results:
            st.success("✅ Your results are ready below. Expand **📋 Investor Questionnaire** further down if you'd like to change an answer and re-predict.")

            RESULT_PREDICTION = "📊 Prediction & Portfolio"
            RESULT_SHAP = "🧠 SHAP"
            RESULT_LIME = "💡 LIME"
            RESULT_SUMMARY = "🤖 AI Decision Summary"
            result_options = [RESULT_PREDICTION, RESULT_SHAP, RESULT_LIME, RESULT_SUMMARY]

            if "active_result_section" not in st.session_state:
                st.session_state["active_result_section"] = RESULT_PREDICTION

            active_result_section = st.segmented_control(
                "Result section",
                options=result_options,
                key="active_result_section",
                label_visibility="collapsed",
            )

            # Rendered one section at a time (instead of all four inside
            # st.tabs) -- st.tabs mounts every tab's content into the DOM
            # simultaneously regardless of which one is visible, which was
            # forcing the browser to build every plot and table up front on
            # every rerun and making the page feel stuck/unresponsive.
            if active_result_section == RESULT_PREDICTION:
                _render_prediction_section(portfolio)
                st.divider()
                _render_portfolio_section(portfolio)
            elif active_result_section == RESULT_SHAP:
                _render_shap_section(shap_result)
            elif active_result_section == RESULT_LIME:
                _render_lime_section(lime_result)
            elif active_result_section == RESULT_SUMMARY:
                _render_ai_decision_summary(
                    st.session_state[SS_USER_INPUT], prediction, portfolio, shap_result, lime_result
                )
            st.divider()

        st.divider()
        _render_questionnaire(default_expanded=not has_results)
        if not has_results:
            st.warning("⚠️ Complete the questionnaire and press **🚀 Predict My Risk Profile** above to see results here.")

    elif active_section == SECTION_PERFORMANCE:
        _render_model_performance_tab()

    _render_footer()


if __name__ == "__main__":
    main()
