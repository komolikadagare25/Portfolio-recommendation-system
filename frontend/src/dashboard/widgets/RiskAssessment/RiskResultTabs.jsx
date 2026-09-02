import React, { useState } from "react";
import { ArrowRight } from "lucide-react";
import PredictionResult from "./PredictionResult";
import PortfolioRecommendation from "./PortfolioRecommendation";
import ShapExplanationPanel from "./ShapExplanationPanel";
import LimeExplanationPanel from "./LimeExplanationPanel";
import { predictionResult, portfolioRecommendation } from "../../../data/predictionMock";
import { shapExplanation } from "../../../data/shapMock";
import { limeExplanation } from "../../../data/limeMock";
import "./RiskResultTabs.css";
import AIDecisionSummary from "./AIDecisionSummary";

const TABS = ["Prediction & Portfolio", "SHAP", "LIME", "AI Decision Summary"];

/**
 * @param {{
 *   onContinue: () => void,
 *   prediction?: object,       // shape of predictionMock.js's predictionResult
 *   portfolio?: object,        // shape of predictionMock.js's portfolioRecommendation
 *   shap?: object,              // shape of shapMock.js's shapExplanation
 *   lime?: object,              // shape of limeMock.js's limeExplanation
 * }} props
 *
 * All four data props are optional — pass real data from your backend once
 * it's wired up (see RiskAssessmentForm.jsx, which calls
 * api/riskAssessment.js). If a prop is omitted, this falls back to the
 * bundled mock so the component still renders standalone during development.
 */
export default function RiskResultTabs({ onContinue, prediction, portfolio, shap, lime, report }) {
  const [activeTab, setActiveTab] = useState("Prediction & Portfolio");

  const predictionData = prediction ?? predictionResult;
  const portfolioData = portfolio ?? portfolioRecommendation;
  const shapData = shap ?? shapExplanation;
  const limeData = lime ?? limeExplanation;

  return (
    <div className="risk-result-tabs">
      <div className="risk-result-tabs__nav">
        {TABS.map((tab) => (
          <button
            key={tab}
            className={`risk-result-tabs__tab ${activeTab === tab ? "risk-result-tabs__tab--active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="risk-result-tabs__content" key={activeTab}>
        {activeTab === "Prediction & Portfolio" && (
          <div className="risk-result-tabs__stack">
            <PredictionResult prediction={predictionData} />
            <PortfolioRecommendation portfolio={portfolioData} />
          </div>
        )}

        {activeTab === "SHAP" && <ShapExplanationPanel explanation={shapData} />}

        {activeTab === "LIME" && <LimeExplanationPanel explanation={limeData} />}

        {activeTab === "AI Decision Summary" && <AIDecisionSummary report={report} />}
      </div>

      {onContinue && (
        <button className="risk-result-tabs__continue-btn" onClick={onContinue}>
          Continue to dashboard <ArrowRight size={16} strokeWidth={2} />
        </button>
      )}
    </div>
  );
}
