import React, { useEffect, useState } from "react";
import "./Recommendations.css";

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

        const latestId = reports[0].id;
        const detailRes = await fetch(`${API_BASE_URL}/reports/${latestId}`, {
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

  return (
    <div className="recommendations-page">
      <h1>Recommendations</h1>
      <p>
        Based on your <strong>{report.risk_level}</strong> risk profile
        (confidence: {(parseFloat(report.confidence) * 100).toFixed(1)}%)
      </p>

      <h2>Recommended Sectors</h2>
      <ul>
        {report.portfolio_result.recommended_sectors.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>

      <h2>Recommended Stocks</h2>
      <ul>
        {report.portfolio_result.recommended_stocks.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>

      <h2>Asset Allocation</h2>
      <ul>
        {Object.entries(report.portfolio_result.asset_allocation).map(([k, v]) => (
          <li key={k}>{k}: {v}%</li>
        ))}
      </ul>

      <p><em>{report.portfolio_result.investment_advice}</em></p>
    </div>
  );
}