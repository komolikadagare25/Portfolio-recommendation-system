"""
portfolio_recommender.py

Rule-Based Portfolio Recommendation Engine
===========================================

This module is part of the "AI-Powered Personalized Stock Portfolio
Recommendation System" (MCA Major Project).

Unlike the upstream Investor Profiling module (Random Forest based),
this module does NOT use any machine learning algorithm. It is a
deterministic, rule-based engine that consumes the risk level and
confidence score produced by the ML prediction module and converts
them into a concrete, human-readable investment portfolio.

Design goals
------------
- Pure, side-effect-free core logic (easy to unit test).
- Configuration-driven: all business rules live in constants/dicts,
  never hardcoded inside function bodies.
- Strict input validation with meaningful exceptions.
- JSON-serializable output so it can be dropped straight into a
  Flask/FastAPI response body.
- Structured logging instead of print statements.

Public API
----------
generate_portfolio(risk_level: str, confidence: float) -> dict
    The single public entry point of this module.

Author: MCA Major Project
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List

# --------------------------------------------------------------------------- #
# Logging configuration
# --------------------------------------------------------------------------- #
logger = logging.getLogger(__name__)
if not logger.handlers:
    # Avoid duplicate handlers if this module is imported multiple times
    # (e.g., by a Flask/FastAPI app with auto-reload).
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _handler.setFormatter(_formatter)
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


# --------------------------------------------------------------------------- #
# Constants & Configuration
# --------------------------------------------------------------------------- #

#: Valid risk levels accepted by this module. Kept as a tuple (immutable)
#: and reused everywhere to avoid magic strings scattered across the code.
VALID_RISK_LEVELS: tuple = ("Conservative", "Moderate", "Aggressive")

#: Minimum and maximum allowed confidence score (inclusive), as produced
#: by the upstream ML prediction module.
MIN_CONFIDENCE: float = 0.0
MAX_CONFIDENCE: float = 1.0

#: Human-readable descriptions for each risk profile.
RISK_DESCRIPTIONS: Dict[str, str] = {
    "Conservative": (
        "You prefer capital safety over high returns and are comfortable "
        "with minimal exposure to market volatility."
    ),
    "Moderate": (
        "You seek a balance between growth and stability, and are "
        "comfortable with moderate market fluctuations."
    ),
    "Aggressive": (
        "You are growth-oriented and willing to accept significant "
        "short-term volatility in pursuit of higher long-term returns."
    ),
}

#: Recommended investment horizon per risk profile.
INVESTMENT_HORIZON: Dict[str, str] = {
    "Conservative": "1-3 Years",
    "Moderate": "3-5 Years",
    "Aggressive": "5-10 Years",
}

#: General investment advice per risk profile.
INVESTMENT_ADVICE: Dict[str, str] = {
    "Conservative": "Focus on capital preservation and low-risk investments.",
    "Moderate": "Maintain a diversified portfolio and rebalance periodically.",
    "Aggressive": (
        "Aim for long-term capital appreciation while accepting higher "
        "market volatility."
    ),
}

#: Asset allocation percentages per risk profile. Values are expressed as
#: whole numbers (percentage points) and should sum to 100 for each profile.
ASSET_ALLOCATION: Dict[str, Dict[str, int]] = {
    "Conservative": {
        "Stocks": 20,
        "Mutual Funds": 20,
        "Government Bonds": 30,
        "Fixed Deposits": 20,
        "Gold": 10,
    },
    "Moderate": {
        "Stocks": 50,
        "Mutual Funds": 25,
        "Government Bonds": 10,
        "Fixed Deposits": 5,
        "Gold": 10,
    },
    "Aggressive": {
        "Stocks": 75,
        "Mutual Funds": 15,
        "Government Bonds": 5,
        "Fixed Deposits": 0,
        "Gold": 5,
    },
}

#: Recommended market sectors per risk profile.
RECOMMENDED_SECTORS: Dict[str, List[str]] = {
    "Conservative": ["Banking", "FMCG", "Utilities"],
    "Moderate": ["IT", "Banking", "Pharmaceuticals"],
    "Aggressive": ["Technology", "Renewable Energy", "AI", "Mid-cap Growth"],
}

#: Mapping of sector name -> representative stocks in that sector.
#: This acts as the single source of truth for stock suggestions and is
#: intentionally kept as static configuration data (no hardcoding inside
#: functions), so it can later be swapped for a database-backed lookup.
SECTOR_STOCK_MAP: Dict[str, List[str]] = {
    "IT": ["TCS", "Infosys", "Wipro"],
    "Banking": ["HDFC Bank", "ICICI Bank", "SBI"],
    "Pharmaceuticals": ["Sun Pharma", "Cipla", "Dr. Reddy's"],
    "FMCG": ["ITC", "Hindustan Unilever", "Nestle India"],
    "Utilities": ["NTPC", "Power Grid"],
    "Technology": ["TCS", "Infosys", "LTIMindtree"],
    "Renewable Energy": ["Tata Power", "Adani Green", "Suzlon"],
    "AI": ["Tata Elxsi", "Persistent Systems"],
    "Mid-cap Growth": ["Dixon Technologies", "Polycab", "Astral"],
}

#: Maximum number of stock recommendations returned to the caller.
MAX_RECOMMENDED_STOCKS: int = 5


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #
class InvalidRiskLevelError(ValueError):
    """Raised when an unsupported risk level string is supplied."""


class InvalidConfidenceScoreError(ValueError):
    """Raised when the confidence score is outside the valid [0, 1] range."""


# --------------------------------------------------------------------------- #
# Data Model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PortfolioRules:
    """
    Immutable container bundling together all rule-based configuration
    for a single risk profile.

    Using a dataclass here (instead of passing around several raw dict
    lookups) keeps the recommendation-building logic readable and makes
    it trivial to unit test each rule set in isolation.
    """

    risk_level: str
    risk_description: str
    investment_horizon: str
    asset_allocation: Dict[str, int]
    recommended_sectors: List[str] = field(default_factory=list)
    investment_advice: str = ""


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #
def _validate_risk_level(risk_level: str) -> str:
    """
    Validate and normalize the supplied risk level.

    Parameters
    ----------
    risk_level : str
        Raw risk level string, e.g. "conservative", "Moderate", "AGGRESSIVE".

    Returns
    -------
    str
        The normalized, title-cased risk level guaranteed to be a key of
        ``VALID_RISK_LEVELS``.

    Raises
    ------
    InvalidRiskLevelError
        If ``risk_level`` is not a string, is empty, or does not match one
        of the supported risk profiles.
    """
    if not isinstance(risk_level, str) or not risk_level.strip():
        raise InvalidRiskLevelError(
            f"risk_level must be a non-empty string, got: {risk_level!r}"
        )

    normalized = risk_level.strip().title()

    if normalized not in VALID_RISK_LEVELS:
        raise InvalidRiskLevelError(
            f"Unsupported risk_level: {risk_level!r}. "
            f"Expected one of {VALID_RISK_LEVELS}."
        )

    return normalized


def _validate_confidence(confidence: float) -> float:
    """
    Validate the confidence score produced by the upstream ML model.

    Parameters
    ----------
    confidence : float
        Confidence score, expected to be a float in the range [0.0, 1.0].

    Returns
    -------
    float
        The validated confidence score, unchanged.

    Raises
    ------
    InvalidConfidenceScoreError
        If ``confidence`` is not numeric or falls outside [0.0, 1.0].
    """
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise InvalidConfidenceScoreError(
            f"confidence must be a numeric value, got: {type(confidence).__name__}"
        )

    if not (MIN_CONFIDENCE <= confidence <= MAX_CONFIDENCE):
        raise InvalidConfidenceScoreError(
            f"confidence must be between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}, "
            f"got: {confidence}"
        )

    return float(confidence)


# --------------------------------------------------------------------------- #
# Core rule-lookup logic
# --------------------------------------------------------------------------- #
def _build_portfolio_rules(risk_level: str) -> PortfolioRules:
    """
    Assemble a :class:`PortfolioRules` instance for a validated risk level
    by pulling data from the module-level configuration dictionaries.

    Parameters
    ----------
    risk_level : str
        A pre-validated, normalized risk level (must be a member of
        ``VALID_RISK_LEVELS``).

    Returns
    -------
    PortfolioRules
        The fully populated rule set for the given risk level.
    """
    return PortfolioRules(
        risk_level=risk_level,
        risk_description=RISK_DESCRIPTIONS[risk_level],
        investment_horizon=INVESTMENT_HORIZON[risk_level],
        asset_allocation=dict(ASSET_ALLOCATION[risk_level]),
        recommended_sectors=list(RECOMMENDED_SECTORS[risk_level]),
        investment_advice=INVESTMENT_ADVICE[risk_level],
    )


def _recommend_stocks(
    sectors: List[str], max_stocks: int = MAX_RECOMMENDED_STOCKS
) -> List[str]:
    """
    Derive a de-duplicated list of recommended stocks from a list of
    recommended sectors, using round-robin selection so that the final
    list draws from as many distinct sectors as possible rather than
    exhausting the first sector before moving to the next.

    Parameters
    ----------
    sectors : List[str]
        Sector names to pull stock suggestions from. Each sector must
        exist as a key in ``SECTOR_STOCK_MAP``.
    max_stocks : int, optional
        Upper bound on the number of stocks returned, by default
        ``MAX_RECOMMENDED_STOCKS``.

    Returns
    -------
    List[str]
        A list of unique stock names, capped at ``max_stocks``.
    """
    per_sector_stocks = [SECTOR_STOCK_MAP.get(sector, []) for sector in sectors]

    recommended: List[str] = []
    seen: set = set()
    index = 0

    while len(recommended) < max_stocks and any(per_sector_stocks):
        made_progress = False
        for stocks in per_sector_stocks:
            if index < len(stocks):
                stock = stocks[index]
                made_progress = True
                if stock not in seen:
                    seen.add(stock)
                    recommended.append(stock)
                    if len(recommended) >= max_stocks:
                        break
        if not made_progress:
            break
        index += 1

    return recommended


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def generate_portfolio(risk_level: str, confidence: float) -> Dict:
    """
    Generate a personalized, rule-based investment portfolio recommendation.

    This is the single public entry point of the ``portfolio_recommender``
    module. It takes the risk level and confidence score produced by the
    upstream Investor Profiling ML module and deterministically maps them
    to a concrete portfolio recommendation using static configuration
    rules (no machine learning is involved at this stage).

    Parameters
    ----------
    risk_level : str
        The predicted investor risk category. Must be one of
        "Conservative", "Moderate", or "Aggressive" (case-insensitive).
    confidence : float
        The prediction confidence score from the ML model, in the range
        [0.0, 1.0].

    Returns
    -------
    Dict
        A JSON-serializable dictionary with the following keys:
        ``risk_level``, ``confidence``, ``risk_description``,
        ``investment_horizon``, ``asset_allocation``,
        ``recommended_sectors``, ``recommended_stocks``,
        ``investment_advice``.

    Raises
    ------
    InvalidRiskLevelError
        If ``risk_level`` is not a supported risk category.
    InvalidConfidenceScoreError
        If ``confidence`` is not a float within [0.0, 1.0].

    Examples
    --------
    >>> result = generate_portfolio("Moderate", 0.87)
    >>> result["risk_level"]
    'Moderate'
    >>> sorted(result["asset_allocation"].keys())
    ['Fixed Deposits', 'Government Bonds', 'Mutual Funds', 'Stocks']
    """
    logger.info(
        "generate_portfolio called with risk_level=%r, confidence=%r",
        risk_level,
        confidence,
    )

    normalized_risk_level = _validate_risk_level(risk_level)
    validated_confidence = _validate_confidence(confidence)

    rules = _build_portfolio_rules(normalized_risk_level)
    recommended_stocks = _recommend_stocks(rules.recommended_sectors)

    portfolio: Dict = {
        "risk_level": rules.risk_level,
        "confidence": round(validated_confidence, 4),
        "risk_description": rules.risk_description,
        "investment_horizon": rules.investment_horizon,
        "asset_allocation": rules.asset_allocation,
        "recommended_sectors": rules.recommended_sectors,
        "recommended_stocks": recommended_stocks,
        "investment_advice": rules.investment_advice,
    }

    logger.info(
        "Portfolio generated successfully for risk_level=%r", rules.risk_level
    )
    return portfolio


# --------------------------------------------------------------------------- #
# Sample usage / manual smoke test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import json

    sample_predictions = [
        {"risk_level": "Conservative", "confidence": 0.88},
        {"risk_level": "Moderate", "confidence": 0.92},
        {"risk_level": "Aggressive", "confidence": 0.95},
    ]

    for prediction in sample_predictions:
        try:
            portfolio_recommendation = generate_portfolio(
                risk_level=prediction["risk_level"],
                confidence=prediction["confidence"],
            )
            print(json.dumps(portfolio_recommendation, indent=4))
            print("-" * 70)
        except (InvalidRiskLevelError, InvalidConfidenceScoreError) as exc:
            logger.error("Failed to generate portfolio: %s", exc)