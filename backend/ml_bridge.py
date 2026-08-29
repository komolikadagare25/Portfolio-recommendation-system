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
from ml.portfolio.src.portfolio_recommender import generate_portfolio, SECTOR_STOCK_MAP, MAX_RECOMMENDED_STOCKS
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
# Stock selection personalization — WHICH stocks get shown, not just %.
# --------------------------------------------------------------------------- #

# Reasonable growth/stability tagging based on company profile (larger,
# established = "stable"; smaller/newer/higher-growth = "growth"). This is
# our own categorization for selection purposes, not derived from live
# volatility data.
STOCK_TYPE_MAP = {
    "TCS": "stable", "Infosys": "stable", "Wipro": "stable",
    "HCL Technologies": "stable", "Tech Mahindra": "stable",
    "HDFC Bank": "stable", "ICICI Bank": "stable", "SBI": "stable",
    "Kotak Mahindra Bank": "stable", "Axis Bank": "stable",
    "Sun Pharma": "stable", "Cipla": "stable", "Dr. Reddy's": "stable",
    "Divi's Laboratories": "stable", "Lupin": "stable",
    "ITC": "stable", "Hindustan Unilever": "stable", "Nestle India": "stable",
    "Britannia Industries": "stable", "Dabur India": "stable",
    "NTPC": "stable", "Power Grid": "stable", "NHPC": "stable",
    "LTIMindtree": "growth", "Tata Power": "growth", "Adani Green": "growth",
    "Suzlon": "growth", "Tata Elxsi": "growth", "Persistent Systems": "growth",
    "Dixon Technologies": "growth", "Polycab": "growth", "Astral": "growth",
    "Adani Power": "growth", "Coforge": "growth", "KPIT Technologies": "growth",
    "JSW Energy": "growth", "Trent": "growth", "Kaynes Technology": "growth",
}

EXPECT_SCORE = {"10%-20%": 0.2, "20%-30%": 0.5, "30%-40%": 0.8}
PURPOSE_SCORE = {"Savings For Future": 0.2, "Returns": 0.5, "Wealth Creation": 0.7}
MONITOR_SCORE = {"Monthly": 0.2, "Weekly": 0.5, "Daily": 0.8}
REASON_EQUITY_SCORE = {"Dividend": 0.2, "Liquidity": 0.4, "Capital Appreciation": 0.8}


def compute_growth_score(model_input: dict) -> float:
    """A 0-1 score from real per-user signals (return appetite, purpose,
    monitoring frequency, reason for equity) — higher means the user's own
    stated preferences lean toward growth over stability."""
    scores = [
        EXPECT_SCORE.get(model_input.get("expect"), 0.5),
        PURPOSE_SCORE.get(model_input.get("purpose"), 0.5),
        MONITOR_SCORE.get(model_input.get("invest_monitor"), 0.5),
        REASON_EQUITY_SCORE.get(model_input.get("reason_equity"), 0.5),
    ]
    return sum(scores) / len(scores)

# Reasonable growth/stability tagging for sectors — same axis as STOCK_TYPE_MAP.
SECTOR_TYPE_MAP = {
    "Banking": "stable", "FMCG": "stable", "Utilities": "stable",
    "Pharmaceuticals": "stable", "IT": "stable",
    "Technology": "growth", "Renewable Energy": "growth",
    "AI": "growth", "Mid-cap Growth": "growth",
}

# One swappable sector slot per risk band: the default sector is swapped
# for the alternative when the user's growth_score clearly leans the
# opposite direction from the band's natural tilt — so even users in the
# same risk band can see a different sector line-up.
SECTOR_SWAP_SLOT = {
    "Conservative": {"default": "Utilities", "alt": "Technology", "alt_when": "growth"},
    "Moderate": {"default": "Pharmaceuticals", "alt": "Renewable Energy", "alt_when": "growth"},
    "Aggressive": {"default": "Mid-cap Growth", "alt": "Banking", "alt_when": "stable"},
}


def personalize_sectors(portfolio: dict, risk_level: str, growth_score: float) -> dict:
    """Swaps one sector in the band template for an alternative when the
    user's growth_score clearly diverges from the band's natural tilt —
    e.g. an Aggressive user with a more moderate growth_score sees Banking
    swapped in for Mid-cap Growth."""
    slot = SECTOR_SWAP_SLOT.get(risk_level)
    sectors = list(portfolio["recommended_sectors"])

    if not slot or slot["default"] not in sectors:
        portfolio["sector_selection_reasoning"] = None
        return portfolio

    leans_growth = growth_score >= 0.6
    leans_stable = growth_score <= 0.4
    should_swap = (slot["alt_when"] == "growth" and leans_growth) or (
        slot["alt_when"] == "stable" and leans_stable
    )

    if should_swap:
        idx = sectors.index(slot["default"])
        sectors[idx] = slot["alt"]
        portfolio["recommended_sectors"] = sectors
        portfolio["sector_selection_reasoning"] = (
            f"Your answers leaned more {'growth-oriented' if slot['alt_when'] == 'growth' else 'stability-focused'} "
            f"than the typical {risk_level} investor, so we swapped {slot['default']} for {slot['alt']} "
            f"in your recommended sectors."
        )
    else:
        portfolio["sector_selection_reasoning"] = None

    return portfolio


def personalize_stock_selection(portfolio: dict, model_input: dict) -> dict:
    """Replaces the band-templated stock list with a per-user selection —
    same sectors, but which specific stock is picked from each sector is
    ordered by the user's own growth_score, so two users in the same risk
    band with different answers see different stock names."""
    growth_score = compute_growth_score(model_input)
    preferred_type = "growth" if growth_score >= 0.5 else "stable"

    sectors = portfolio["recommended_sectors"]
    per_sector_candidates = []
    for sector in sectors:
        candidates = list(SECTOR_STOCK_MAP.get(sector, []))
        candidates.sort(key=lambda s: STOCK_TYPE_MAP.get(s, "stable") != preferred_type)
        per_sector_candidates.append(candidates)

    selected = []
    seen = set()
    round_index = 0
    while len(selected) < MAX_RECOMMENDED_STOCKS and any(
        round_index < len(c) for c in per_sector_candidates
    ):
        for candidates in per_sector_candidates:
            if round_index < len(candidates):
                stock = candidates[round_index]
                if stock not in seen:
                    selected.append(stock)
                    seen.add(stock)
                    if len(selected) >= MAX_RECOMMENDED_STOCKS:
                        break
        round_index += 1

    portfolio["recommended_stocks"] = selected
    portfolio["stock_selection_reasoning"] = (
        f"Based on your stated return expectations, investment purpose, "
        f"monitoring frequency, and reason for choosing equities, we leaned "
        f"toward {'growth-oriented' if preferred_type == 'growth' else 'stable, established'} "
        f"picks within your recommended sectors."
    )
    return portfolio

def build_category_guidance(model_input: dict, growth_score: float) -> dict:
    """Personalized, per-user guidance for the non-stock allocation
    categories — grounded in real signals (Duration, Invest_Monitor,
    growth_score), not a generic one-size-fits-all message."""
    duration = model_input.get("duration")
    monitor = model_input.get("invest_monitor")

    if growth_score >= 0.6:
        mutual_funds = (
            "Consider a Nifty 50 index fund (UTI or Navi Nifty 50, ~0.06-0.2% expense ratio) "
            "as your core holding, plus a Nifty Next 50 index fund (e.g. HDFC Nifty Next 50) for "
            "extra growth tilt, matching your growth-leaning answers."
        )
    else:
        mutual_funds = (
            "Consider a pure Nifty 50 index fund — UTI Nifty 50 Index Fund is well-established, "
            "Navi Nifty 50 Index Fund has one of the lowest expense ratios (~0.06%). All Nifty 50 "
            "index funds hold the same 50 stocks in the same weights, so cost matters more than brand."
        )

    if duration == "More Than 5 Years":
        gold = (
            "With your 5+ year horizon, consider a Sovereign Gold Bond (SGB) — issued by RBI, "
            "tax-free if held to maturity (8 years), better suited to a long hold than an ETF."
        )
    elif monitor == "Daily":
        gold = (
            "Since you check investments daily, a liquid Gold ETF (Nippon India Gold BeES: "
            "GOLDBEES, or SBI Gold ETF: SETFGOLD) suits you better than an SGB, since ETFs trade "
            "freely on the exchange any market day."
        )
    else:
        gold = (
            "Consider Nippon India ETF Gold BeES (GOLDBEES) or SBI Gold ETF (SETFGOLD) — liquid, "
            "established gold ETFs on the NSE that track physical gold without needing storage."
        )

    if duration in ("Less Than 1 Year", "1-3 Years"):
        govt_bonds = (
            f"Given your {duration.lower()} horizon, look for shorter-tenure government securities "
            "or treasury bills via RBI Retail Direct (rbiretaildirect.org.in) rather than long-dated bonds."
        )
    else:
        govt_bonds = (
            f"Given your {duration.lower() if duration else 'longer'} horizon, longer-tenure "
            "government securities via RBI Retail Direct (rbiretaildirect.org.in) can lock in "
            "current yields for longer."
        )

    fixed_deposits = (
        f"Look for an FD with a tenure close to your {duration.lower() if duration else 'stated'} "
        "horizon for the best matching rate — compare 2-3 banks first, since rates vary and change over time."
    )

    return {
        "Mutual Funds": mutual_funds,
        "Government Bonds": govt_bonds,
        "Fixed Deposits": fixed_deposits,
        "Gold": gold,
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
    growth_score = compute_growth_score(model_input)
    portfolio = personalize_sectors(portfolio, risk_level, growth_score)
    portfolio = personalize_stock_selection(portfolio, model_input)
    portfolio["category_guidance"] = build_category_guidance(model_input, growth_score)

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