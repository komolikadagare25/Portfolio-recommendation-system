import React, { useState } from "react";
import LimeContributionChart from "./LimeContributionChart";
import LimeTopFeaturesTable from "./LimeTopFeaturesTable";
import LimePlainExplanation from "./LimePlainExplanation";
import "./LimeExplanationPanel.css";

const CHART_TABS = ["Local Feature Weights"];

/**
 * @param {{ explanation: {
 *   predictedBand: string,
 *   confidence: number,
 *   intercept: number,
 *   localModelScore: number,
 *   features: Array<{feature:string, condition:string, weight:number}>
 * } }} props
 */
export default function LimeExplanationPanel({ explanation }) {
  const [activeTab, setActiveTab] = useState("Local Feature Weights");
  const { predictedBand, confidence, intercept, localModelScore, features } = explanation;

  const sortedByMagnitude = [...features].sort((a, b) => Math.abs(b.weight) - Math.abs(a.weight));
  const topPositive = [...features].filter((f) => f.weight >= 0).sort((a, b) => b.weight - a.weight);
  const topNegative = [...features].filter((f) => f.weight < 0).sort((a, b) => a.weight - b.weight);

  return (
    <div className="lime-panel">
      <div className="lime-panel__header">
        <span className="lime-panel__icon">🔍</span>
        <h2 className="lime-panel__title">Explainable AI using LIME</h2>
      </div>
      <p className="lime-panel__subtitle">
        Explaining prediction: <strong>{predictedBand}</strong> (confidence: {confidence}%)
      </p>

            {(intercept !== undefined || localModelScore !== undefined) && (
        <div className="lime-panel__meta-row">
          {intercept !== undefined && (
            <div className="lime-panel__meta-item">
              <span className="lime-panel__meta-label">Local model intercept</span>
              <span className="lime-panel__meta-value">{intercept.toFixed(4)}</span>
            </div>
          )}
          {localModelScore !== undefined && (
            <div className="lime-panel__meta-item">
              <span className="lime-panel__meta-label">Local model fit (R²)</span>
              <span className="lime-panel__meta-value">{localModelScore.toFixed(2)}</span>
            </div>
          )}
        </div>
      )}

      <div className="lime-panel__chart-tabs">
        {CHART_TABS.map((tab) => (
          <button
            key={tab}
            className={`lime-panel__chart-tab ${activeTab === tab ? "lime-panel__chart-tab--active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="lime-panel__chart-card">
        <p className="lime-panel__chart-title">Feature Contributions to Prediction (Local Surrogate Model)</p>
        <LimeContributionChart features={sortedByMagnitude} />
      </div>

      <div className="lime-panel__section">
        <LimeTopFeaturesTable features={features} />
      </div>

      <div className="lime-panel__section">
        <LimePlainExplanation
          predictedBand={predictedBand}
          topPositive={topPositive}
          topNegative={topNegative}
        />
      </div>
    </div>
  );
}
