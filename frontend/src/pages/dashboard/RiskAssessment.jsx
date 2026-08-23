import React from "react";
import { useNavigate } from "react-router-dom";
import RiskAssessmentForm from "../../dashboard/widgets/RiskAssessment/RiskAssessmentForm";
import "./RiskAssessment.css";

export default function RiskAssessment() {
  const navigate = useNavigate();

  const handleComplete = (answers) => {
    // `answers` keys match your dataset columns exactly, e.g.:
    // { age: 29, gender: "Male", Investment_Avenues: "Yes", Factor: "Risk", ... }
    //
    // TODO: once your backend endpoint exists, send it like this:
    // const res = await fetch("/api/risk-assessment", {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify(answers),
    // });
    // const { risk_level, confidence } = await res.json();
    // then store risk_level/confidence (e.g. via AuthContext) before navigating.

    console.log("Risk assessment answers (ready for backend):", answers);
    navigate("/dashboard");
  };

  return (
    <div className="risk-assessment-page">
      <h1>Risk Assessment</h1>
      <p>Answer these questions so we can tailor your recommendations.</p>
      <RiskAssessmentForm onComplete={handleComplete} />
    </div>
  );
}
