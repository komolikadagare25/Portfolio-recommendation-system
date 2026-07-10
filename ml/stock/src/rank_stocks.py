"""Rank and recommend stocks within a selected risk category.

This module is a stock-ranking engine for the Explainable AI-Based
Portfolio Recommendation System pipeline. Given a selected risk
category (Low Risk / Medium Risk / High Risk), it computes per-stock
historical return and volatility metrics from
`ml/data/processed/labeled_training_dataset.csv`, scores and ranks
stocks within that category, and produces a simple equal-weight
allocation for a hypothetical investment amount.

This module does NOT use any investor/user financial profile -- the
risk category is selected directly (default: Medium Risk), not
derived from a user. Matching an individual investor to a risk
category is the responsibility of a future, separate Investor Risk
Classifier module.

This module MUST NOT:
    * Use SHAP or LIME.
    * Implement portfolio optimization, Modern Portfolio Theory,
      Black-Litterman, Monte Carlo simulation, or CAPM.
    * Depend on Flask or React.

Typical usage:
    python -m src.rank_stocks
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------
import logging
from pathlib import Path
from typing import Final, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------------
# Configuration / Constants
# ----------------------------------------------------------------------------
# ml/src/rank_stocks.py -> parent (src) -> parent (ml)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Input file produced by generate_risk_labels.py.
INPUT_FILEPATH: Final[Path] = BASE_DIR / "data" / "processed" / "labeled_training_dataset.csv"

#: Directory where text/CSV reports are saved.
REPORTS_DIR: Final[Path] = BASE_DIR / "reports"

#: Output path for the recommended stocks CSV.
OUTPUT_FILEPATH: Final[Path] = REPORTS_DIR / "recommended_stocks.csv"

#: Directory where figures are saved.
FIGURES_DIR: Final[Path] = REPORTS_DIR / "figures"

#: Filename for the recommended stocks bar chart.
RECOMMENDED_STOCKS_PLOT_FILENAME: Final[str] = "recommended_stocks.png"

#: Trading days per year, used to annualize daily return/volatility.
TRADING_DAYS_PER_YEAR: Final[int] = 252

#: Valid risk categories, matching the labels produced by generate_risk_labels.py.
VALID_RISK_LEVELS: Final[list] = ["Low Risk", "Medium Risk", "High Risk"]

#: Risk category to rank within. This is a direct selection, not derived
#: from any user/investor profile.
SELECTED_RISK_LEVEL: Final[str] = "Medium Risk"

#: Hypothetical total investment amount (in INR) to allocate.
INVESTMENT_AMOUNT: Final[float] = 100_000.0

#: Number of top-ranked stocks to recommend.
TOP_N: Final[int] = 5

#: Small constant to avoid division by zero when volatility is ~0.
EPSILON: Final[float] = 1e-9

#: Columns that together uniquely identify a row.
ROW_IDENTIFIER_COLUMNS: Final[list] = ["Stock", "Date"]

#: Logging verbosity for this module.
LOG_LEVEL: Final[int] = logging.INFO

# ----------------------------------------------------------------------------
# Logger
# ----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def _configure_logging() -> None:
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
def load_labeled_dataset(filepath: Path) -> pd.DataFrame:
    """Load the labeled training dataset produced by generate_risk_labels.py.

    Args:
        filepath: Path to `labeled_training_dataset.csv`.

    Returns:
        The loaded DataFrame with the Date column parsed as datetime.
    """
    logger.debug("Loading labeled dataset: %s", filepath)
    return pd.read_csv(filepath, parse_dates=["Date"])


# ----------------------------------------------------------------------------
# Validation Functions
# ----------------------------------------------------------------------------
def validate_input_file_exists(filepath: Path) -> bool:
    """Verify that the required input file exists on disk.

    Args:
        filepath: Path to the expected input CSV file.

    Returns:
        True if the file exists, False otherwise.
    """
    if not filepath.exists():
        logger.error("Input file not found: %s", filepath)
        return False
    return True


def validate_no_missing_risk_level(df: pd.DataFrame) -> bool:
    """Verify every row has a non-null Risk_Level.

    Args:
        df: The loaded labeled dataset.

    Returns:
        True if `Risk_Level` has zero missing values, False otherwise.
    """
    missing_count = int(df["Risk_Level"].isna().sum())

    if missing_count > 0:
        logger.error("%d row(s) have a missing Risk_Level.", missing_count)
        return False

    return True


def validate_investment_amount(investment: float) -> bool:
    """Verify the investment amount is a positive number.

    Args:
        investment: The hypothetical amount to allocate.

    Returns:
        True if `investment` is greater than zero, False otherwise.
    """
    if investment <= 0:
        logger.error("Investment amount must be greater than 0, got: %s", investment)
        return False

    return True


def validate_risk_level(risk_level: str) -> bool:
    """Verify the selected risk category is one of the known valid categories.

    Args:
        risk_level: The requested risk category.

    Returns:
        True if `risk_level` is one of `VALID_RISK_LEVELS`, False
        otherwise.
    """
    if risk_level not in VALID_RISK_LEVELS:
        logger.error(
            "Invalid risk category '%s'. Must be one of: %s",
            risk_level,
            VALID_RISK_LEVELS,
        )
        return False

    return True


def validate_inputs(df: pd.DataFrame, investment: float, risk_level: str) -> bool:
    """Run all validation checks required before ranking stocks.

    Args:
        df: The loaded labeled dataset.
        investment: The hypothetical amount to allocate.
        risk_level: The requested risk category.

    Returns:
        True only if every individual validation check passes, False
        if any check fails.
    """
    checks = {
        "no missing Risk_Level": validate_no_missing_risk_level(df),
        "investment > 0": validate_investment_amount(investment),
        "risk category valid": validate_risk_level(risk_level),
    }

    for check_name, passed in checks.items():
        logger.info("Validation check '%s': %s", check_name, "PASSED" if passed else "FAILED")

    return all(checks.values())


# ----------------------------------------------------------------------------
# Ranking Functions
# ----------------------------------------------------------------------------
def build_stock_metrics_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build a per-stock table of historical return, volatility, and price metrics.

    For each stock, calculates:
        * Average Annual Return: mean(Daily Return) * 252 * 100
        * Average Annual Volatility: std(Daily Return) * sqrt(252) * 100
        * Latest Close Price: Close on the most recent Date
        * Latest Adj Close: Adj Close on the most recent Date
        * Risk_Level: the stock's assigned risk category

    "Average Annual Return" here is the annualized rate implied by the
    stock's mean daily return, computed the same way as Average Annual
    Volatility (from the mean/std of Daily Return) so both metrics are
    derived consistently. This is distinct from the total-period
    compounded return computed in generate_risk_labels.py.

    Args:
        df: The labeled training dataset.

    Returns:
        A DataFrame with one row per stock and columns `Stock`,
        `Risk_Level`, `Average Annual Return`, `Average Annual
        Volatility`, `Latest Close Price`, `Latest Adj Close`.
    """
    sorted_df = df.sort_values(ROW_IDENTIFIER_COLUMNS)
    grouped = sorted_df.groupby("Stock")

    average_annual_return = grouped["Daily Return"].mean() * TRADING_DAYS_PER_YEAR * 100
    average_annual_volatility = grouped["Daily Return"].std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100
    latest_rows = grouped.tail(1).set_index("Stock")
    risk_level_per_stock = grouped["Risk_Level"].first()

    metrics = pd.DataFrame(
        {
            "Stock": average_annual_return.index,
            "Risk_Level": risk_level_per_stock.reindex(average_annual_return.index).values,
            "Average Annual Return": average_annual_return.values,
            "Average Annual Volatility": average_annual_volatility.reindex(average_annual_return.index).values,
            "Latest Close Price": latest_rows["Close"].reindex(average_annual_return.index).values,
            "Latest Adj Close": latest_rows["Adj Close"].reindex(average_annual_return.index).values,
        }
    )
    return metrics


def filter_by_risk_level(metrics_df: pd.DataFrame, risk_level: str) -> pd.DataFrame:
    """Filter the per-stock metrics table down to a single risk category.

    Args:
        metrics_df: The full per-stock metrics table.
        risk_level: The risk category to keep.

    Returns:
        A new DataFrame containing only stocks whose `Risk_Level`
        matches `risk_level`.
    """
    return metrics_df[metrics_df["Risk_Level"] == risk_level].copy()


def calculate_recommendation_score(df: pd.DataFrame) -> pd.DataFrame:
    """Add a Recommendation Score column based on return per unit of risk.

    Recommendation Score = Average Annual Return / Average Annual Volatility

    This is a simple, transparent return-to-risk ratio: a higher score
    means more historical annual return was earned per unit of annual
    volatility. It uses only the two metrics already computed in
    `build_stock_metrics_table` -- no risk-free rate, benchmark, or
    market assumptions are involved, so this is not a Sharpe Ratio,
    CAPM-based measure, or any other named financial risk-adjustment
    model.

    Args:
        df: A per-stock metrics table (already filtered by risk
            category) with `Average Annual Return` and `Average
            Annual Volatility` columns.

    Returns:
        A new DataFrame with a `Recommendation Score` column added.
    """
    result = df.copy()
    safe_volatility = result["Average Annual Volatility"].replace(0, EPSILON)
    result["Recommendation Score"] = result["Average Annual Return"] / safe_volatility
    return result


def rank_top_stocks(df: pd.DataFrame) -> pd.DataFrame:
    """Sort stocks by Recommendation Score and keep the top N.

    Args:
        df: A per-stock metrics table with a `Recommendation Score`
            column.

    Returns:
        A new DataFrame containing the top `TOP_N` stocks, sorted
        descending by `Recommendation Score`, with a `Rank` column
        added (1 = best).
    """
    ranked = df.sort_values("Recommendation Score", ascending=False).head(TOP_N).reset_index(drop=True)
    ranked.insert(0, "Rank", range(1, len(ranked) + 1))
    return ranked


# ----------------------------------------------------------------------------
# Allocation Functions
# ----------------------------------------------------------------------------
def allocate_investment(df: pd.DataFrame, investment: float) -> pd.DataFrame:
    """Allocate a hypothetical investment equally across the top-ranked stocks.

    Splits `investment` evenly across all rows in `df`, then computes
    the approximate whole number of shares affordable at each stock's
    `Latest Close Price` and the resulting leftover (uninvested) cash.

    Args:
        df: The top-ranked stocks table.
        investment: The total hypothetical amount to allocate.

    Returns:
        A new DataFrame with `Investment Allocated`, `Approximate
        Shares`, and `Remaining Cash` columns added.
    """
    result = df.copy()
    investment_per_stock = investment / len(result)

    result["Investment Allocated"] = investment_per_stock
    result["Approximate Shares"] = np.floor(investment_per_stock / result["Latest Close Price"]).astype(int)
    result["Remaining Cash"] = investment_per_stock - (result["Approximate Shares"] * result["Latest Close Price"])

    return result


def estimate_expected_portfolio_value(df: pd.DataFrame) -> pd.DataFrame:
    """Estimate each stock's contribution to portfolio value after one year.

    Expected Value After 1 Year = Investment Allocated * (1 + Average
    Annual Return / 100). This is purely an extrapolation of each
    stock's historical average annual return and is NOT a guarantee
    of future performance.

    Args:
        df: The allocated top-ranked stocks table.

    Returns:
        A new DataFrame with an `Expected Value After 1 Year (Estimate)`
        column added.
    """
    result = df.copy()
    result["Expected Value After 1 Year (Estimate)"] = result["Investment Allocated"] * (
        1 + result["Average Annual Return"] / 100
    )
    return result


# ----------------------------------------------------------------------------
# Save Functions
# ----------------------------------------------------------------------------
def save_recommendations(df: pd.DataFrame) -> Path:
    """Persist the final recommended stocks table to a CSV file.

    Args:
        df: The fully ranked, allocated, and estimated stocks table.

    Returns:
        The path the CSV file was written to.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILEPATH, index=False)
    return OUTPUT_FILEPATH


def plot_recommended_stocks(df: pd.DataFrame, risk_level: str) -> Path:
    """Create and save a horizontal bar chart of the top recommended stocks.

    Bars represent each stock's Recommendation Score, ordered so the
    top-ranked stock appears at the top of the chart.

    Args:
        df: The top-ranked stocks table, containing `Stock` and
            `Recommendation Score` columns.
        risk_level: The risk category these recommendations belong
            to, used in the chart title.

    Returns:
        The path the figure was saved to.
    """
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    plot_df = df.sort_values("Recommendation Score", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(plot_df["Stock"], plot_df["Recommendation Score"])
    ax.set_title(f"Top Recommended Stocks ({risk_level})")
    ax.set_xlabel("Recommendation Score")
    ax.set_ylabel("Stock")
    ax.grid(True, axis="x")
    fig.tight_layout()

    filepath = FIGURES_DIR / RECOMMENDED_STOCKS_PLOT_FILENAME
    fig.savefig(filepath)
    plt.close(fig)

    return filepath


# ----------------------------------------------------------------------------
# Main Function
# ----------------------------------------------------------------------------
def main() -> None:
    """Rank and recommend stocks within the selected risk category.

    Orchestrates: validate input exists -> load dataset -> validate
    inputs -> build per-stock metrics -> filter by risk category ->
    score -> rank top N -> allocate investment -> estimate expected
    value -> save CSV -> plot -> log a full summary. Aborts early if
    the input file is missing or any validation check fails.
    """
    logger.info("Starting stock ranking for risk category: %s", SELECTED_RISK_LEVEL)

    if not validate_input_file_exists(INPUT_FILEPATH):
        logger.error("Aborting: required input file is missing.")
        return

    df = load_labeled_dataset(INPUT_FILEPATH)

    if not validate_inputs(df, INVESTMENT_AMOUNT, SELECTED_RISK_LEVEL):
        logger.error("Validation failed. Aborting.")
        return

    metrics_df = build_stock_metrics_table(df)
    filtered_df = filter_by_risk_level(metrics_df, SELECTED_RISK_LEVEL)

    if filtered_df.empty:
        logger.error("No stocks found for risk category '%s'. Aborting.", SELECTED_RISK_LEVEL)
        return

    logger.info("Stocks available in '%s' category: %s", SELECTED_RISK_LEVEL, filtered_df["Stock"].tolist())

    scored_df = calculate_recommendation_score(filtered_df)
    top_stocks_df = rank_top_stocks(scored_df)

    allocated_df = allocate_investment(top_stocks_df, INVESTMENT_AMOUNT)
    final_df = estimate_expected_portfolio_value(allocated_df)

    total_invested = final_df["Investment Allocated"].sum()
    total_remaining_cash = final_df["Remaining Cash"].sum()
    total_expected_value = final_df["Expected Value After 1 Year (Estimate)"].sum() + total_remaining_cash

    logger.info("===== Stock Recommendation Summary =====")
    logger.info("Selected risk category: %s", SELECTED_RISK_LEVEL)
    logger.info("Investment amount: INR %.2f", INVESTMENT_AMOUNT)
    logger.info(
        "Top %d recommended stocks:\n%s",
        TOP_N,
        final_df[["Rank", "Stock", "Average Annual Return", "Average Annual Volatility", "Recommendation Score"]].to_string(index=False),
    )
    logger.info(
        "Allocation detail:\n%s",
        final_df[["Stock", "Latest Close Price", "Investment Allocated", "Approximate Shares", "Remaining Cash"]].to_string(index=False),
    )
    logger.info("Total invested across top %d stocks: INR %.2f", TOP_N, total_invested)
    logger.info("Total remaining (uninvested) cash: INR %.2f", total_remaining_cash)
    logger.info(
        "Estimated total portfolio value after 1 year: INR %.2f "
        "(THIS IS AN ESTIMATE based on each stock's historical average annual return, "
        "not a guarantee of future performance)",
        total_expected_value,
    )
    logger.info("==========================================")

    saved_path = save_recommendations(final_df)
    plot_path = plot_recommended_stocks(final_df, SELECTED_RISK_LEVEL)

    logger.info(
        "Stock ranking complete. Saved CSV: %s | Saved plot: %s",
        saved_path,
        plot_path,
    )


# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    _configure_logging()
    main()