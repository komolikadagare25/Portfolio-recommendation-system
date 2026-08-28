import React from "react";
import { useNavigate } from "react-router-dom";
import RiskAssessmentForm from "../../dashboard/widgets/RiskAssessment/RiskAssessmentForm";
import "./RiskAssessment.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

export default function RiskAssessment() {
  const navigate = useNavigate();

  const submitAnswers = async (answers) => {
    const token = localStorage.getItem("access_token");

    const res = await fetch(`${API_BASE_URL}/reports`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ questionnaire_answers: answers }),
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`Report creation failed (${res.status}): ${text}`);
    }

    return res.json();
  };

  const handleComplete = () => {
    // The report was already saved by submitAnswers before this screen showed.
    navigate("/dashboard");
  };

  return (
    <div className="risk-assessment-page">
      <h1>Risk Assessment</h1>
      <p>Answer these questions so we can tailor your recommendations.</p>
      <RiskAssessmentForm onSubmitAnswers={submitAnswers} onComplete={handleComplete} />
    </div>
  );
}