import React, { useState } from "react";
import ShapContributionChart from "./ShapContributionChart";
import ShapTopFeaturesTable from "./ShapTopFeaturesTable";
import ShapPlainExplanation from "./ShapPlainExplanation";
import "./ShapExplanationPanel.css";

const CHART_TABS = ["Summary Plot", "Bar Plot", "Waterfall Plot"];

/**
 * @param {{ explanation: { predictedBand: string, confidence: number, features: Array<{feature:string,value:number}> } }} props
 */
export default function ShapExplanationPanel({ explanation }) {
  const [activeTab, setActiveTab] = useState("Bar Plot");
  const { predictedBand, confidence, features } = explanation;

  const sortedByMagnitude = [...features].sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
  const topPositive = [...features].filter((f) => f.value >= 0).sort((a, b) => b.value - a.value);
  const topNegative = [...features].filter((f) => f.value < 0).sort((a, b) => a.value - b.value);

  return (
    <div className="shap-panel">
      <div className="shap-panel__header">
        <span className="shap-panel__icon">🧠</span>
        <h2 className="shap-panel__title">Explainable AI using SHAP</h2>
      </div>
      <p className="shap-panel__subtitle">
        Explaining prediction: <strong>{predictedBand}</strong> (confidence: {confidence}%)
      </p>

      <div className="shap-panel__chart-tabs">
        {CHART_TABS.map((tab) => (
          <button
            key={tab}
            className={`shap-panel__chart-tab ${activeTab === tab ? "shap-panel__chart-tab--active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="shap-panel__chart-card">
        {activeTab === "Bar Plot" ? (
          <>
            <p className="shap-panel__chart-title">Feature Contributions to Prediction</p>
            <ShapContributionChart features={sortedByMagnitude} />
          </>
        ) : (
          <p className="shap-panel__chart-placeholder">
            {activeTab} isn't wired up yet — Bar Plot uses the same data and is fully working.
          </p>
        )}
      </div>

      <div className="shap-panel__section">
        <ShapTopFeaturesTable features={features} />
      </div>

      <div className="shap-panel__section">
        <ShapPlainExplanation
          predictedBand={predictedBand}
          topPositive={topPositive}
          topNegative={topNegative}
        />
      </div>
    </div>
  );
}
