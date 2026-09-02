import React from "react";
import { CheckCircle2 } from "lucide-react";
import CollapsibleSection from "./CollapsibleSection";
import "./PredictionResult.css";

/**
 * @param {{ prediction: {
 *   riskLevel: string, confidence: number, investmentHorizon: string, riskDescription: string,
 *   investorSummary: { age: number|string, objective: string, preferredAsset: string, duration: string }
 * } }} props
 */
const RISK_TONE = {
  Low: "prediction-result__stat-value--low",
  Medium: "prediction-result__stat-value--medium",
  High: "prediction-result__stat-value--high",
};

export default function PredictionResult({ prediction }) {
  const { riskLevel, confidence, investmentHorizon, riskDescription, investorSummary } = prediction;

  return (
    <div className="prediction-result">
      <div className="prediction-result__header">
        <span className="prediction-result__icon">📊</span>
        <h2 className="prediction-result__title">Prediction Result</h2>
      </div>

      <div className="prediction-result__stats-row">
        <div className="prediction-result__stat">
          <p className="prediction-result__stat-label">Risk Level</p>
          <p className={`prediction-result__stat-value ${RISK_TONE[riskLevel] || ""}`}>{riskLevel}</p>
        </div>
        <div className="prediction-result__stat">
          <p className="prediction-result__stat-label">Confidence</p>
          <p className="prediction-result__stat-value">{confidence}%</p>
        </div>
        <div className="prediction-result__stat">
          <p className="prediction-result__stat-label">Investment Horizon</p>
          <p className="prediction-result__stat-value">{investmentHorizon}</p>
        </div>
        <div className="prediction-result__complete-badge">
          <CheckCircle2 size={16} strokeWidth={2} />
          Prediction complete
        </div>
      </div>

      <div className="prediction-result__description-banner">
        <strong>Risk Description:</strong> {riskDescription}
      </div>

      <CollapsibleSection icon="📄" title="Investor Summary">
        <div className="prediction-result__summary-grid">
          <div>
            <p className="prediction-result__summary-label">Age</p>
            <p className="prediction-result__summary-value">{investorSummary.age}</p>
          </div>
          <div>
            <p className="prediction-result__summary-label">Investment Objective</p>
            <p className="prediction-result__summary-value">{investorSummary.objective}</p>
          </div>
          <div>
            <p className="prediction-result__summary-label">Preferred Asset</p>
            <p className="prediction-result__summary-value">{investorSummary.preferredAsset}</p>
          </div>
          <div>
            <p className="prediction-result__summary-label">Duration</p>
            <p className="prediction-result__summary-value">{investorSummary.duration}</p>
          </div>
        </div>
      </CollapsibleSection>
    </div>
  );
}
