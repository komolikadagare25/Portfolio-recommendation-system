// Mock SHAP output shaped exactly like your Streamlit prototype's response.
// Replace this whole file with the real API response once your backend
// exposes a SHAP endpoint (e.g. POST /api/risk-assessment/explain).
//
// Exact values (from your screenshot's Top Positive/Negative tables) are used
// for the top 5 each way; the remaining smaller features are illustrative
// placeholders matching the bar chart's relative sizes — replace all of it
// with the real explainer output.

export const shapExplanation = {
  predictedBand: "Conservative",
  confidence: 36.72,
  // Sorted by |value| descending, matches the bar plot order in your screenshot.
  features: [
    { feature: "equity_market", value: -0.1335 },
    { feature: "ppf", value: 0.1172 },
    { feature: "fixed_deposits", value: 0.0784 },
    { feature: "mutual_funds", value: -0.0471 },
    { feature: "duration", value: 0.0312 },
    { feature: "debentures", value: -0.0274 },
    { feature: "government_bonds", value: 0.0225 },
    { feature: "gold", value: 0.0207 },
    { feature: "age", value: -0.0182 },
    { feature: "reason_fd", value: -0.015 },
    { feature: "source", value: 0.008 },
    { feature: "reason_bonds", value: -0.006 },
    { feature: "reason_mutual", value: 0.004 },
    { feature: "investment_avenues", value: -0.003 },
    { feature: "stock_market", value: -0.003 },
    { feature: "invest_monitor", value: 0.003 },
    { feature: "avenue", value: 0.003 },
    { feature: "objective", value: -0.002 },
    { feature: "factor", value: -0.002 },
    { feature: "reason_equity", value: 0.002 },
    { feature: "expect", value: 0.001 },
    { feature: "gender", value: 0.001 },
    { feature: "purpose", value: 0.001 },
    { feature: "what_are_your_savings_objectives", value: 0.0005 },
  ],
};
