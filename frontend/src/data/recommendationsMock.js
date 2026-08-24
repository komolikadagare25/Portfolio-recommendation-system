// Full recommendations list for the Recommendations page (the dashboard's
// RecommendedStocksTable only shows a short preview of this same data).
// Replace with a real API call once it exists, e.g.:
//   GET /api/recommendations               -> recommendedStocks
//   GET /api/recommendations/:symbol/why   -> { shap: [...], lime: [...] } per stock
//
// `reasons.shap` / `reasons.lime` are short, already-worded bullets (not raw
// feature arrays) since this page shows many stocks at once — for the full
// numeric breakdown of a single prediction, that's what the SHAP/LIME tabs
// on the Risk Assessment result are for.

export const recommendedStocks = [
  {
    symbol: "INFY",
    name: "Infosys Ltd.",
    sector: "Technology",
    weight: 15,
    expReturn: 18.2,
    risk: "Low",
    reasons: {
      shap: [
        "Your PPF and Fixed Deposit preference pushed the model toward stable, dividend-paying large-caps like this one.",
        "Low reported exposure to Equity Market slightly favored lower-volatility technology names over high-beta ones.",
      ],
      lime: [
        "Locally, 'fixed_deposits > 4.00' was the strongest driver toward this pick.",
        "'equity_market <= 2.00' also supported a lower-volatility large-cap over a growth-heavy one.",
      ],
    },
  },
  {
    symbol: "HDFCBANK",
    name: "HDFC Bank Ltd.",
    sector: "Banking",
    weight: 10,
    expReturn: 12.5,
    risk: "Low",
    reasons: {
      shap: [
        "Government Bonds preference correlated with a preference for stable, regulated-sector holdings like banking.",
        "Short investment duration (Less Than 1 Year) favored liquid, large-cap names over small-caps.",
      ],
      lime: [
        "'duration = Less Than 1 Year' was the top local driver toward liquid large-caps.",
        "'government_bonds > 3.00' reinforced a preference for regulated, stable-earnings sectors.",
      ],
    },
  },
  {
    symbol: "HINDUNILVR",
    name: "Hindustan Unilever",
    sector: "FMCG",
    weight: 12,
    expReturn: 10.8,
    risk: "Low",
    reasons: {
      shap: [
        "Conservative predicted band strongly favors defensive, low-beta sectors such as FMCG.",
        "PPF preference is historically associated with investors who also hold defensive equity.",
      ],
      lime: [
        "'ppf > 3.00' was the strongest local push toward defensive-sector holdings.",
        "Low equity market exposure kept high-beta sectors out of this recommendation.",
      ],
    },
  },
  {
    symbol: "TATASTEEL",
    name: "Tata Steel Ltd.",
    sector: "Infra",
    weight: 8,
    expReturn: 22.1,
    risk: "Medium",
    reasons: {
      shap: [
        "Included as a small satellite position — Gold and Government Bonds answers left room for one cyclical holding.",
        "Age band contributed a small positive weight toward some growth exposure.",
      ],
      lime: [
        "'gold > 2.00' locally allowed one higher-beta satellite position within an otherwise conservative mix.",
        "Weight is capped low (8%) since most local drivers pointed toward defensive holdings.",
      ],
    },
  },
  {
    symbol: "ITC",
    name: "ITC Ltd.",
    sector: "FMCG",
    weight: 9,
    expReturn: 9.6,
    risk: "Low",
    reasons: {
      shap: [
        "Fixed Deposit preference and Conservative band both favor dividend-yield defensive names.",
        "Diversifies sector exposure alongside Hindustan Unilever without adding volatility.",
      ],
      lime: [
        "'fixed_deposits > 4.00' was a strong local driver toward high dividend-yield FMCG.",
        "'reason_fd = Safety' reinforced the preference for capital-safety-oriented holdings.",
      ],
    },
  },
  {
    symbol: "NTPC",
    name: "NTPC Ltd.",
    sector: "Infra",
    weight: 7,
    expReturn: 11.4,
    risk: "Low",
    reasons: {
      shap: [
        "Government Bonds preference correlates with comfort holding regulated, government-linked utilities.",
        "Low Equity Market exposure kept this pick in the utility segment rather than industrial cyclicals.",
      ],
      lime: [
        "'government_bonds > 3.00' was the top local driver toward a regulated utility name.",
        "'duration = Less Than 1 Year' supported a steady-dividend, low-volatility holding.",
      ],
    },
  },
  {
    symbol: "ICICIBANK",
    name: "ICICI Bank Ltd.",
    sector: "Banking",
    weight: 8,
    expReturn: 14.3,
    risk: "Medium",
    reasons: {
      shap: [
        "Source = Bank Advisor had a small positive weight, correlating with comfort in banking-sector holdings.",
        "Balances HDFC Bank's weight with a second, slightly higher-growth banking name.",
      ],
      lime: [
        "'source = Bank Advisor' was a modest local driver toward this pick.",
        "Weighted lower than HDFC Bank since most local drivers favored the lower-volatility peer.",
      ],
    },
  },
  {
    symbol: "SUNPHARMA",
    name: "Sun Pharmaceutical Ltd.",
    sector: "Pharma",
    weight: 6,
    expReturn: 13.7,
    risk: "Low",
    reasons: {
      shap: [
        "Pharma is a defensive sector consistent with the Conservative predicted band.",
        "Adds sector diversification (7 sectors total) without raising portfolio volatility.",
      ],
      lime: [
        "No single feature dominates locally — this pick is mainly explained by the overall Conservative local model score.",
        "'age <= 27.00' had a small negative weight, slightly capping this position's size.",
      ],
    },
  },
  {
    symbol: "ADANIPORTS",
    name: "Adani Ports & SEZ",
    sector: "Infra",
    weight: 5,
    expReturn: 24.8,
    risk: "High",
    reasons: {
      shap: [
        "Smallest position in the list — included only because Gold answer left minor room for a higher-growth satellite.",
        "Equity Market and Mutual Funds answers pushed against a larger allocation here.",
      ],
      lime: [
        "'equity_market <= 2.00' worked against this pick locally, which is why its weight is capped at 5%.",
        "'mutual_funds <= 1.00' also worked against a larger high-growth allocation.",
      ],
    },
  },
];
