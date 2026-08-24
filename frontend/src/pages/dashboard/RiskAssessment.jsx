import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import RiskAssessmentForm from "../../dashboard/widgets/RiskAssessment/RiskAssessmentForm";
import "./RiskAssessment.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

export default function RiskAssessment() {
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleComplete = async (answers) => {
    setSubmitting(true);
    setError(null);

    const token = localStorage.getItem("access_token");

    try {
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

      const report = await res.json();
      console.log("Report saved:", report);
      navigate("/dashboard");
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="risk-assessment-page">
      <h1>Risk Assessment</h1>
      <p>Answer these questions so we can tailor your recommendations.</p>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {submitting && <p>Generating your report...</p>}
      <RiskAssessmentForm onComplete={handleComplete} />
    </div>
  );
}