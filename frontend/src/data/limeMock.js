// // Mock LIME output, shaped the way `lime.lime_tabular.LimeTabularExplainer`
// // actually returns it: an intercept (local model's baseline) + a ranked list
// // of (feature, human-readable condition, weight) tuples from the local
// // linear surrogate model fit around this one prediction.
// //
// // Replace this whole file with the real API response once your backend
// // exposes a LIME endpoint (e.g. POST /api/risk-assessment/explain-lime).
// // Feature names line up with shapMock.js so both tabs describe the same
// // prediction — values differ because LIME and SHAP compute contributions
// // differently (local linear surrogate vs. Shapley values).

// export const limeExplanation = {
//   predictedBand: "Conservative",
//   confidence: 36.72,
//   // Local model's intercept — the baseline score before any feature's
//   // contribution is added, in this neighborhood of the data.
//   intercept: 0.2891,
//   // Local surrogate model's own fit quality for this one explanation.
//   localModelScore: 0.87,
//   // Sorted by |weight| descending, matches LIME's default bar plot order.
//   features: [
//     { feature: "equity_market", condition: "equity_market <= 2.00", weight: -0.1187 },
//     { feature: "ppf", condition: "ppf > 3.00", weight: 0.1029 },
//     { feature: "fixed_deposits", condition: "fixed_deposits > 4.00", weight: 0.0713 },
//     { feature: "mutual_funds", condition: "mutual_funds <= 1.00", weight: -0.0498 },
//     { feature: "duration", condition: "duration = Less Than 1 Year", weight: 0.0356 },
//     { feature: "debentures", condition: "debentures <= 2.00", weight: -0.0241 },
//     { feature: "government_bonds", condition: "government_bonds > 3.00", weight: 0.0219 },
//     { feature: "gold", condition: "gold > 2.00", weight: 0.0184 },
//     { feature: "age", condition: "age <= 27.00", weight: -0.0166 },
//     { feature: "reason_fd", condition: "reason_fd = Safety", weight: -0.0132 },
//     { feature: "source", condition: "source = Bank Advisor", weight: 0.0091 },
//     { feature: "reason_bonds", condition: "reason_bonds = Fixed Returns", weight: -0.0057 },
//     { feature: "reason_mutual", condition: "reason_mutual = Growth", weight: 0.0045 },
//     { feature: "investment_avenues", condition: "investment_avenues <= 3.00", weight: -0.0034 },
//     { feature: "stock_market", condition: "stock_market <= 2.00", weight: -0.0028 },
//     { feature: "invest_monitor", condition: "invest_monitor = Monthly", weight: 0.0026 },
//     { feature: "avenue", condition: "avenue = Mutual Fund", weight: 0.0024 },
//     { feature: "objective", condition: "objective = Growth", weight: -0.0019 },
//     { feature: "factor", condition: "factor = Returns", weight: -0.0017 },
//     { feature: "reason_equity", condition: "reason_equity = High Growth", weight: 0.0015 },
//     { feature: "expect", condition: "expect = 10-20%", weight: 0.0009 },
//     { feature: "gender", condition: "gender = Female", weight: 0.0008 },
//     { feature: "purpose", condition: "purpose = Wealth Creation", weight: 0.0006 },
//     { feature: "what_are_your_savings_objectives", condition: "objective_savings = Retirement", weight: 0.0004 },
//   ],
// };
