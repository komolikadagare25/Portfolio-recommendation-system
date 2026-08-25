import React from "react";
import { useNavigate } from "react-router-dom";
import RiskAssessmentForm from "../../dashboard/widgets/RiskAssessment/RiskAssessmentForm";
import { usePortfolio } from "../../context/PortfolioContext";
import "./RiskAssessment.css";

export default function RiskAssessment() {
  const navigate = useNavigate();
  const { setResult } = usePortfolio();

  // `result` is the real backend response once /api/risk-assessment exists:
  // { prediction, portfolio, shap, lime } — see api/riskAssessment.js for the
  // exact shape. `answers` are the raw questionnaire answers (dataset-column
  // keys) in case you want to log/send them anywhere else too.
  const handleComplete = (result, answers) => {
    setResult(result);
    navigate("/dashboard/portfolio");
  };

  return (
    <div className="risk-assessment-page">
      <h1>Risk Assessment</h1>
      <p>Answer these questions so we can tailor your recommendations.</p>
      <RiskAssessmentForm onComplete={handleComplete} />
    </div>
  );
}
