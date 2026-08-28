import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardList, ArrowRight } from "lucide-react";
import "./MyPortfolio.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

export default function MyPortfolio() {
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

  if (loading) return <div className="myPortfolio-page"><h1>My Portfolio</h1><p>Loading...</p></div>;
  if (error) return <div className="myPortfolio-page"><h1>My Portfolio</h1><p style={{ color: "red" }}>{error}</p></div>;

  if (!report) {
    return (
      <div className="myPortfolio-page">
        <h1>My Portfolio</h1>
        <p>Your personalized risk profile and recommended allocation will appear here.</p>

        <div className="myPortfolio-empty">
          <div className="myPortfolio-empty__icon">
            <ClipboardList size={26} strokeWidth={1.75} />
          </div>
          <h2>No portfolio yet</h2>
          <p>
            Complete the Risk Assessment questionnaire and we'll generate your risk
            profile, asset allocation, and stock recommendations here.
          </p>
          <Link to="/dashboard/risk-assessment" className="myPortfolio-empty__cta">
            Take the Risk Assessment <ArrowRight size={16} strokeWidth={2} />
          </Link>
        </div>
      </div>
    );
  }

  const { portfolio_result } = report;

  return (
    <div className="myPortfolio-page">
      <h1>My Portfolio</h1>
      <p>
        Based on your <strong>{report.risk_level}</strong> risk profile
        (confidence: {(parseFloat(report.confidence) * 100).toFixed(1)}%)
      </p>

      <h2>Asset Allocation</h2>
      <ul>
        {Object.entries(portfolio_result.asset_allocation).map(([k, v]) => (
          <li key={k}>{k}: {v}%</li>
        ))}
      </ul>

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
    </div>
  );
}