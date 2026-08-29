import React from "react";
import ShapPlainExplanation from "./ShapPlainExplanation";
import LimePlainExplanation from "./LimePlainExplanation";

/**
 * Consolidates everything the pipeline can genuinely explain about a
 * report: why this risk category was predicted (SHAP + LIME, reusing the
 * same plain-language components as the Recommendations page), why the
 * allocation differs from the standard template, and why these specific
 * stocks were chosen. Nothing here is invented — every sentence traces
 * back to a real computed value in the report.
 *
 * @param {{ report: object }} props - the raw report object from the backend
 */
export default function AIDecisionSummary({ report }) {
  if (!report) return null;

  const { risk_level, shap_result, lime_result, portfolio_result } = report;
  const explanation = portfolio_result?.personalization_explanation;

  const limeFeatures = lime_result.top_features.map((f) => ({
    feature: f.feature,
    condition: f.feature,
    weight: f.weight,
  }));
  const limeTopPositive = limeFeatures.filter((f) => f.weight >= 0).sort((a, b) => b.weight - a.weight);
  const limeTopNegative = limeFeatures.filter((f) => f.weight < 0).sort((a, b) => a.weight - b.weight);

  return (
    <div className="risk-result-tabs__stack">
      <div>
        <h3>1. Why this risk category?</h3>
        <ShapPlainExplanation
          predictedBand={risk_level}
          topPositive={shap_result.top_positive_features}
          topNegative={shap_result.top_negative_features}
        />
        <LimePlainExplanation
          predictedBand={risk_level}
          topPositive={limeTopPositive}
          topNegative={limeTopNegative}
        />
      </div>

      {explanation && (
        <div>
          <h3>2. Why this allocation?</h3>
          <p>{explanation.summary}</p>
        </div>
      )}

            {portfolio_result?.sector_selection_reasoning && (
        <div>
          <h3>3. Why these sectors?</h3>
          <p>{portfolio_result.sector_selection_reasoning}</p>
        </div>
      )}

      {portfolio_result?.stock_selection_reasoning && (
        <div>
          <h3>4. Why these specific stocks?</h3>
          <p>{portfolio_result.stock_selection_reasoning}</p>
        </div>
      )}
    </div>
  );
}