import React, { useEffect, useState } from "react";
import ShapPlainExplanation from "../../dashboard/widgets/RiskAssessment/ShapPlainExplanation";
import LimePlainExplanation from "../../dashboard/widgets/RiskAssessment/LimePlainExplanation";
import "./Recommendations.css";
import BeginnerGuide from "../../dashboard/widgets/RiskAssessment/BeginnerGuide";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

export default function Recommendations() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const token = localStorage.getItem("access_token");

  useEffect(() => {
    async function loadLatestReport() {
      try {
        const listRes = await fetch(`${API_BASE_URL}/reports`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!listRes.ok) throw new Error(`Failed to load reports (${listRes.status})`);
        const reports = await listRes.json();

        if (reports.length === 0) {
          setLoading(false);
          return;
        }

        const detailRes = await fetch(`${API_BASE_URL}/reports/${reports[0].id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!detailRes.ok) throw new Error(`Failed to load report (${detailRes.status})`);
        setReport(await detailRes.json());
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadLatestReport();
  }, [token]);

  if (loading) return <div className="recommendations-page"><h1>Recommendations</h1><p>Loading...</p></div>;
  if (error) return <div className="recommendations-page"><h1>Recommendations</h1><p style={{ color: "red" }}>{error}</p></div>;

  if (!report) {
    return (
      <div className="recommendations-page">
        <h1>Recommendations</h1>
        <p>No reports yet — complete a Risk Assessment to see recommendations.</p>
      </div>
    );
  }

  const { portfolio_result, shap_result, lime_result, risk_level } = report;

  const shapTopPositive = shap_result.top_positive_features;
  const shapTopNegative = shap_result.top_negative_features;

  // LIME's `feature` string already includes its threshold condition
  // (e.g. "3.00 < equity_market <= 4.00"), so we reuse it as `condition` too.
  const limeFeatures = lime_result.top_features.map((f) => ({
    feature: f.feature,
    condition: f.feature,
    weight: f.weight,
  }));
  const limeTopPositive = limeFeatures.filter((f) => f.weight >= 0).sort((a, b) => b.weight - a.weight);
  const limeTopNegative = limeFeatures.filter((f) => f.weight < 0).sort((a, b) => a.weight - b.weight);

  return (
    <div className="recommendations-page">
      <h1>Recommendations</h1>
      <p>
        Based on your <strong>{risk_level}</strong> risk profile
        (confidence: {(parseFloat(report.confidence) * 100).toFixed(1)}%)
      </p>

      <h2>Recommended Sectors</h2>
      <ul>
        {portfolio_result.recommended_sectors.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>

      <h2>Recommended Stocks</h2>
      <ul>
        {portfolio_result.recommended_stocks.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>

            <p><em>{portfolio_result.investment_advice}</em></p>

      {portfolio_result.personalization_explanation && (
        <>
          <h2>Why your allocation looks like this</h2>
          <p>{portfolio_result.personalization_explanation.summary}</p>

          <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: "16px" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>
                <th style={{ padding: "6px" }}>Category</th>
                <th style={{ padding: "6px" }}>Standard Template</th>
                <th style={{ padding: "6px" }}>Your Allocation</th>
                <th style={{ padding: "6px" }}>Change</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(portfolio_result.personalization_explanation.final_allocation).map(([category, finalVal]) => {
                const baseVal = portfolio_result.personalization_explanation.base_allocation[category];
                const delta = finalVal - baseVal;
                return (
                  <tr key={category} style={{ borderBottom: "1px solid #f0f0f0" }}>
                    <td style={{ padding: "6px" }}>{category}</td>
                    <td style={{ padding: "6px" }}>{baseVal}%</td>
                    <td style={{ padding: "6px" }}>{finalVal}%</td>
                    <td style={{ padding: "6px", color: delta > 0 ? "green" : delta < 0 ? "red" : "#666" }}>
                      {delta > 0 ? "+" : ""}{delta}pts
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}

      <h2>Why these recommendations?</h2>
      <ShapPlainExplanation
        predictedBand={risk_level}
        topPositive={shapTopPositive}
        topNegative={shapTopNegative}
      />
      <LimePlainExplanation
        predictedBand={risk_level}
        topPositive={limeTopPositive}
        topNegative={limeTopNegative}
      />
      <BeginnerGuide />
    </div>
  );
}