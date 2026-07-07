"""Generate data-driven risk labels for every stock in the training dataset.

This module is the risk-labeling stage of the Explainable AI-Based
Portfolio Recommendation System pipeline. Its sole responsibility is
to compute a Risk_Level ("Low Risk" / "Medium Risk" / "High Risk") for
each stock -- derived from historical annual return and annual
volatility via unsupervised clustering -- and attach that label to
every row belonging to that stock.

Risk levels are never hardcoded and no arbitrary thresholds are used;
the boundary between risk categories emerges from KMeans clustering
on standardized (Annual Return, Annual Volatility) pairs, one pair
per stock.

This module MUST NOT:
    * Perform feature engineering.
    * Train or evaluate a supervised ML model.
    * Perform stock recommendation.

Those responsibilities belong to other stages of the pipeline.

Typical usage:
    python -m src.generate_risk_labels
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
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ----------------------------------------------------------------------------
# Configuration / Constants
# ----------------------------------------------------------------------------
# ml/src/generate_risk_labels.py -> parent (src) -> parent (ml)
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent

#: Directory holding the combined training dataset.
PROCESSED_DATA_DIR: Final[Path] = BASE_DIR / "data" / "processed"

#: Input file produced by prepare_training_data.py.
INPUT_FILEPATH: Final[Path] = PROCESSED_DATA_DIR / "training_dataset.csv"

#: Output file containing the original data plus Risk_Level.
OUTPUT_FILEPATH: Final[Path] = PROCESSED_DATA_DIR / "labeled_training_dataset.csv"

#: Directory where the risk-cluster scatter plot is saved.
FIGURES_DIR: Final[Path] = BASE_DIR / "reports" / "figures"

#: Filename for the risk-cluster scatter plot.
RISK_CLUSTER_PLOT_FILENAME: Final[str] = "risk_clusters.png"

#: Trading days per year, used to annualize daily volatility.
TRADING_DAYS_PER_YEAR: Final[int] = 252

#: Number of risk clusters to form.
N_CLUSTERS: Final[int] = 3

#: Random seed for reproducible clustering.
RANDOM_STATE: Final[int] = 42

#: Number of centroid-seed initializations for KMeans.
N_INIT: Final[int] = 10

#: Risk category labels, ordered from lowest to highest volatility.
RISK_LEVELS_ORDERED: Final[list] = ["Low Risk", "Medium Risk", "High Risk"]

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


# ----------------------------------------------------------------------------
# Core Functions -- Loading
# ----------------------------------------------------------------------------
def load_training_dataset(filepath: Path) -> pd.DataFrame:
    """Load the combined training dataset produced by prepare_training_data.py.

    Args:
        filepath: Path to `training_dataset.csv`.

    Returns:
        The loaded DataFrame with the Date column parsed as datetime.
    """
    logger.debug("Loading training dataset: %s", filepath)
    return pd.read_csv(filepath, parse_dates=["Date"])


# ----------------------------------------------------------------------------
# Core Functions -- Risk Metric Calculation
# ----------------------------------------------------------------------------
def calculate_annual_return(df: pd.DataFrame) -> pd.Series:
    """Calculate annualized return per stock over the dataset's date range.

    Computed as ``((last Adj Close / first Adj Close) - 1) * 100`` per
    stock, using each stock's earliest and latest available date in
    the dataset.

    Args:
        df: The training dataset, containing `Stock`, `Date`, and
            `Adj Close` columns.

    Returns:
        A Series indexed by `Stock` with each stock's annual return
        (in percent).
    """
    sorted_df = df.sort_values(ROW_IDENTIFIER_COLUMNS)

    def _return_for_group(group: pd.DataFrame) -> float:
        first_price = group["Adj Close"].iloc[0]
        last_price = group["Adj Close"].iloc[-1]
        return ((last_price / first_price) - 1) * 100

    return sorted_df.groupby("Stock").apply(_return_for_group, include_groups=False)


def calculate_annual_volatility(df: pd.DataFrame) -> pd.Series:
    """Calculate annualized volatility per stock from daily returns.

    Computed as ``std(Daily Return) * sqrt(TRADING_DAYS_PER_YEAR) * 100``
    per stock.

    Args:
        df: The training dataset, containing `Stock` and `Daily
            Return` columns.

    Returns:
        A Series indexed by `Stock` with each stock's annual
        volatility (in percent).
    """
    daily_std = df.groupby("Stock")["Daily Return"].std()
    return daily_std * np.sqrt(TRADING_DAYS_PER_YEAR) * 100


def build_risk_metrics_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build a per-stock table of annual return and annual volatility.

    Args:
        df: The training dataset.

    Returns:
        A DataFrame with columns `Ticker`, `Annual Return`, and
        `Annual Volatility`, one row per stock.
    """
    annual_return = calculate_annual_return(df)
    annual_volatility = calculate_annual_volatility(df)

    metrics = pd.DataFrame(
        {
            "Ticker": annual_return.index,
            "Annual Return": annual_return.values,
            "Annual Volatility": annual_volatility.reindex(annual_return.index).values,
        }
    )
    return metrics


# ----------------------------------------------------------------------------
# Core Functions -- Clustering
# ----------------------------------------------------------------------------
def standardize_features(metrics_df: pd.DataFrame) -> np.ndarray:
    """Standardize Annual Return and Annual Volatility to zero mean, unit variance.

    Args:
        metrics_df: A DataFrame with `Annual Return` and `Annual
            Volatility` columns.

    Returns:
        A 2D numpy array of standardized feature values, in the same
        row order as `metrics_df`.
    """
    scaler = StandardScaler()
    return scaler.fit_transform(metrics_df[["Annual Return", "Annual Volatility"]])


def run_kmeans_clustering(scaled_features: np.ndarray) -> np.ndarray:
    """Run KMeans clustering on standardized risk features.

    Args:
        scaled_features: A 2D array of standardized (Annual Return,
            Annual Volatility) pairs.

    Returns:
        A 1D array of cluster labels (arbitrary integers), one per
        row of `scaled_features`.
    """
    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=N_INIT)
    return kmeans.fit_predict(scaled_features)


def map_clusters_to_risk_levels(metrics_df: pd.DataFrame) -> dict:
    """Map arbitrary KMeans cluster IDs to ordered risk level names.

    KMeans cluster numbers carry no inherent order, so clusters are
    ranked by their mean Annual Volatility (ascending) and assigned
    `RISK_LEVELS_ORDERED` accordingly -- the lowest-volatility cluster
    becomes "Low Risk", and so on.

    Args:
        metrics_df: A DataFrame with `Annual Volatility` and `Cluster`
            columns.

    Returns:
        A dict mapping each raw cluster ID to its risk level name.
    """
    cluster_mean_volatility = (
        metrics_df.groupby("Cluster")["Annual Volatility"].mean().sort_values()
    )

    ordered_cluster_ids = cluster_mean_volatility.index.tolist()
    return dict(zip(ordered_cluster_ids, RISK_LEVELS_ORDERED))


def assign_risk_levels(df: pd.DataFrame, metrics_df: pd.DataFrame) -> pd.DataFrame:
    """Attach a Risk_Level column to every row based on its stock's category.

    Args:
        df: The original training dataset.
        metrics_df: The per-stock metrics table, containing `Ticker`
            and `Risk_Level` columns.

    Returns:
        A new DataFrame identical to `df` with a `Risk_Level` column
        added, based on each row's `Stock`.
    """
    ticker_to_risk_level = metrics_df.set_index("Ticker")["Risk_Level"]
    result = df.copy()
    result["Risk_Level"] = result["Stock"].map(ticker_to_risk_level)
    return result


# ----------------------------------------------------------------------------
# Core Functions -- Validation
# ----------------------------------------------------------------------------
def validate_no_missing_risk_level(df: pd.DataFrame) -> bool:
    """Verify every row has a non-null Risk_Level.

    Args:
        df: The labeled dataset.

    Returns:
        True if `Risk_Level` has zero missing values, False otherwise.
    """
    missing_count = int(df["Risk_Level"].isna().sum())

    if missing_count > 0:
        logger.error("%d row(s) have a missing Risk_Level.", missing_count)
        return False

    return True


def validate_one_label_per_stock(df: pd.DataFrame) -> bool:
    """Verify each stock maps to exactly one Risk_Level.

    Args:
        df: The labeled dataset.

    Returns:
        True if every stock has exactly one distinct Risk_Level
        across all of its rows, False otherwise.
    """
    labels_per_stock = df.groupby("Stock")["Risk_Level"].nunique()
    inconsistent_stocks = labels_per_stock[labels_per_stock != 1]

    if not inconsistent_stocks.empty:
        logger.error(
            "Stock(s) with inconsistent Risk_Level assignment: %s",
            inconsistent_stocks.index.tolist(),
        )
        return False

    return True


def validate_exactly_three_labels(df: pd.DataFrame) -> bool:
    """Verify exactly three distinct Risk_Level values exist.

    Args:
        df: The labeled dataset.

    Returns:
        True if exactly `N_CLUSTERS` (3) distinct Risk_Level values
        are present, False otherwise.
    """
    distinct_labels = df["Risk_Level"].nunique()

    if distinct_labels != N_CLUSTERS:
        logger.error(
            "Expected exactly %d distinct Risk_Level values, found %d: %s",
            N_CLUSTERS,
            distinct_labels,
            sorted(df["Risk_Level"].dropna().unique().tolist()),
        )
        return False

    return True


def validate_no_duplicate_rows(df: pd.DataFrame) -> bool:
    """Verify there are no duplicate (Stock, Date) rows.

    Args:
        df: The labeled dataset.

    Returns:
        True if no duplicate (Stock, Date) pairs exist, False
        otherwise.
    """
    duplicate_count = int(df.duplicated(subset=ROW_IDENTIFIER_COLUMNS).sum())

    if duplicate_count > 0:
        logger.error("Found %d duplicate (Stock, Date) row(s).", duplicate_count)
        return False

    return True


def validate_dataset(df: pd.DataFrame) -> bool:
    """Run all validation checks required before saving the labeled dataset.

    Args:
        df: The fully labeled dataset, immediately before saving.

    Returns:
        True only if every individual validation check passes, False
        if any check fails.
    """
    checks = {
        "no missing Risk_Level": validate_no_missing_risk_level(df),
        "exactly one label per stock": validate_one_label_per_stock(df),
        "exactly three distinct labels": validate_exactly_three_labels(df),
        "no duplicate (Stock, Date) rows": validate_no_duplicate_rows(df),
    }

    for check_name, passed in checks.items():
        logger.info("Validation check '%s': %s", check_name, "PASSED" if passed else "FAILED")

    return all(checks.values())


# ----------------------------------------------------------------------------
# Core Functions -- Summary, Save, Visualization
# ----------------------------------------------------------------------------
def summarize_dataset(df: pd.DataFrame, metrics_df: pd.DataFrame, cluster_mapping: dict) -> None:
    """Log a detailed summary of the labeled dataset and clustering outcome.

    Args:
        df: The final labeled dataset.
        metrics_df: The per-stock metrics table with `Cluster` and
            `Risk_Level` columns.
        cluster_mapping: The raw-cluster-ID to risk-level-name mapping.
    """
    rows_per_risk_level = df["Risk_Level"].value_counts()
    stocks_per_risk_level = metrics_df.groupby("Risk_Level")["Ticker"].apply(list)
    memory_usage_mb = df.memory_usage(deep=True).sum() / (1024 ** 2)

    logger.info("===== Risk Labeling Summary =====")
    logger.info("Number of stocks: %d", df["Stock"].nunique())
    logger.info("Total rows: %d", len(df))
    logger.info("Rows per risk level:")
    for risk_level, count in rows_per_risk_level.items():
        logger.info("  %s: %d rows", risk_level, count)
    logger.info("Stocks per risk level:")
    for risk_level, tickers in stocks_per_risk_level.items():
        logger.info("  %s (%d): %s", risk_level, len(tickers), tickers)
    logger.info("Annual Return table:\n%s", metrics_df[["Ticker", "Annual Return"]].to_string(index=False))
    logger.info("Annual Volatility table:\n%s", metrics_df[["Ticker", "Annual Volatility"]].to_string(index=False))
    logger.info("Cluster mapping (raw cluster ID -> Risk_Level): %s", cluster_mapping)
    logger.info("Dataset shape: %s", df.shape)
    logger.info("Memory usage: %.2f MB", memory_usage_mb)
    logger.info("==================================")


def save_labeled_dataset(df: pd.DataFrame) -> Path:
    """Persist the labeled dataset to the processed data directory.

    Args:
        df: The final, validated labeled dataset.

    Returns:
        The path the CSV file was written to.
    """
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILEPATH, index=False)
    return OUTPUT_FILEPATH


def plot_risk_clusters(metrics_df: pd.DataFrame) -> Path:
    """Create and save a scatter plot of stocks by risk cluster.

    Plots Annual Volatility (x-axis) against Annual Return (y-axis),
    colored by raw KMeans cluster ID, with every point annotated by
    its ticker.

    Args:
        metrics_df: The per-stock metrics table with `Cluster` column.

    Returns:
        The path the figure was saved to.
    """
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 8))

    scatter = ax.scatter(
        metrics_df["Annual Volatility"],
        metrics_df["Annual Return"],
        c=metrics_df["Cluster"],
        cmap="viridis",
        s=80,
    )

    for _, row in metrics_df.iterrows():
        ax.annotate(
            row["Ticker"],
            (row["Annual Volatility"], row["Annual Return"]),
            textcoords="offset points",
            xytext=(5, 5),
        )

    ax.set_title("Risk Cluster Scatter Plot")
    ax.set_xlabel("Annual Volatility (%)")
    ax.set_ylabel("Annual Return (%)")
    ax.grid(True)
    legend_handles, _ = scatter.legend_elements()
    ax.legend(legend_handles, [f"Cluster {c}" for c in sorted(metrics_df["Cluster"].unique())])
    fig.tight_layout()

    filepath = FIGURES_DIR / RISK_CLUSTER_PLOT_FILENAME
    fig.savefig(filepath)
    plt.close(fig)

    return filepath


# ----------------------------------------------------------------------------
# Main Function
# ----------------------------------------------------------------------------
def main() -> None:
    """Generate, validate, save, and visualize data-driven risk labels.

    Orchestrates: validate input exists -> load dataset -> compute
    per-stock annual return/volatility -> standardize -> cluster with
    KMeans -> map clusters to Low/Medium/High risk by volatility ->
    assign labels to every row -> validate -> summarize -> save ->
    plot. If validation fails, the labeled dataset is not saved.
    """
    logger.info("Starting risk label generation.")

    if not validate_input_file_exists(INPUT_FILEPATH):
        logger.error("Aborting: required input file is missing.")
        return

    df = load_training_dataset(INPUT_FILEPATH)

    metrics_df = build_risk_metrics_table(df)
    scaled_features = standardize_features(metrics_df)
    metrics_df["Cluster"] = run_kmeans_clustering(scaled_features)

    cluster_mapping = map_clusters_to_risk_levels(metrics_df)
    metrics_df["Risk_Level"] = metrics_df["Cluster"].map(cluster_mapping)

    labeled_df = assign_risk_levels(df, metrics_df)

    if not validate_dataset(labeled_df):
        logger.error("Validation failed. Labeled dataset was NOT saved.")
        return

    summarize_dataset(labeled_df, metrics_df, cluster_mapping)
    saved_path = save_labeled_dataset(labeled_df)
    plot_path = plot_risk_clusters(metrics_df)

    logger.info(
        "Risk label generation complete. Saved dataset: %s | Saved plot: %s",
        saved_path,
        plot_path,
    )


# ----------------------------------------------------------------------------
# Entry Point
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    _configure_logging()
    main()