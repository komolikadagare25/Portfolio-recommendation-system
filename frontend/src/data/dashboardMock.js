// Mock data for DashboardHome. Replace each of these with a real API call
// once your backend endpoints exist, e.g.:
//   GET /api/portfolio/summary        -> stats + riskProfile
//   GET /api/portfolio/allocation     -> allocation
//   GET /api/portfolio/shap           -> shapFeatures
//   GET /api/recommendations?limit=4  -> recommendedStocks

export const riskProfile = {
  band: "Medium Risk",
  lastAssessed: "14 Jun 2026",
  modelVersion: "v2.3",
  confidence: 82.4,
};

export const stats = [
  { label: "PORTFOLIO VALUE", value: "₹2,48,000", caption: "+12.4% est. annual", tone: "up" },
  { label: "EXPECTED RETURN", value: "14.2%", caption: "Above Nifty avg", tone: "up" },
  { label: "RISK SCORE", value: "54 / 100", caption: "Medium zone", tone: "warn" },
  { label: "DIVERSIFICATION", value: "7 sectors", caption: "Well diversified", tone: "up" },
];

export const allocation = [
  { label: "Technology", value: 30, color: "#3b82f6" },
  { label: "FMCG", value: 22, color: "#22c55e" },
  { label: "Banking", value: 15, color: "#f59e0b" },
  { label: "Pharma", value: 10, color: "#8b5cf6" },
  { label: "Infrastructure", value: 23, color: "#14b8a6" },
];

export const shapFeatures = [
  { name: "Investment Horizon", value: 0.44 },
  { name: "Age", value: 0.34 },
  { name: "Monthly Income", value: 0.27 },
  { name: "Loss Tolerance", value: -0.22 },
  { name: "Exp. Level", value: -0.14 },
  { name: "Liquidity Need", value: -0.09 },
];

export const recommendedStocks = [
  { symbol: "INFY", name: "Infosys Ltd.", sector: "Technology", weight: 15, expReturn: 18.2, risk: "Low" },
  { symbol: "HDFCBANK", name: "HDFC Bank Ltd.", sector: "Banking", weight: 10, expReturn: 12.5, risk: "Low" },
  { symbol: "HINDUNILVR", name: "Hindustan Unilever", sector: "FMCG", weight: 12, expReturn: 10.8, risk: "Low" },
  { symbol: "TATASTEEL", name: "Tata Steel Ltd.", sector: "Infra", weight: 8, expReturn: 22.1, risk: "Medium" },
];
