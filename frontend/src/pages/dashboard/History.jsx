import React, { useEffect, useState } from "react";
import "./History.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

export default function History() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);
  const [selectedLoading, setSelectedLoading] = useState(false);

  const token = localStorage.getItem("access_token");

  useEffect(() => {
    async function loadReports() {
      try {
        const res = await fetch(`${API_BASE_URL}/reports`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Failed to load reports (${res.status})`);
        const data = await res.json();
        setReports(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadReports();
  }, [token]);

  const openReport = async (reportId) => {
    setSelectedLoading(true);
    setSelectedReport(null);
    try {
      const res = await fetch(`${API_BASE_URL}/reports/${reportId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed to load report (${res.status})`);
      const data = await res.json();
      setSelectedReport(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setSelectedLoading(false);
    }
  };

  if (loading) return <div className="history-page"><h1>History</h1><p>Loading...</p></div>;
  if (error) return <div className="history-page"><h1>History</h1><p style={{ color: "red" }}>{error}</p></div>;

  return (
    <div className="history-page">
      <h1>History</h1>

      {reports.length === 0 && <p>No reports yet — complete a Risk Assessment to generate one.</p>}

      <div style={{ display: "flex", gap: "24px", alignItems: "flex-start" }}>
        <ul style={{ listStyle: "none", padding: 0, minWidth: "280px" }}>
          {reports.map((r) => (
            <li key={r.id} style={{ marginBottom: "8px" }}>
              <button
                onClick={() => openReport(r.id)}
                style={{
                  width: "100%",
                  textAlign: "left",
                  padding: "12px",
                  border: "1px solid #ddd",
                  borderRadius: "8px",
                  background: selectedReport?.id === r.id ? "#eef4ff" : "#fff",
                  cursor: "pointer",
                }}
              >
                <div style={{ fontWeight: 600 }}>{r.risk_level}</div>
                <div style={{ fontSize: "0.85em", color: "#666" }}>
                  Confidence: {(parseFloat(r.confidence) * 100).toFixed(1)}%
                </div>
                <div style={{ fontSize: "0.8em", color: "#999" }}>
                  {new Date(r.created_at).toLocaleString()}
                </div>
              </button>
            </li>
          ))}
        </ul>

        {selectedLoading && <p>Loading report...</p>}

        {selectedReport && (
          <div style={{ flex: 1, padding: "16px", border: "1px solid #ddd", borderRadius: "8px" }}>
            <h2>{selectedReport.risk_level} Risk</h2>
            <p>Confidence: {(parseFloat(selectedReport.confidence) * 100).toFixed(1)}%</p>
            <p>{selectedReport.portfolio_result.risk_description}</p>

            <h3>Asset Allocation</h3>
            <ul>
              {Object.entries(selectedReport.portfolio_result.asset_allocation).map(([k, v]) => (
                <li key={k}>{k}: {v}%</li>
              ))}
            </ul>

            <h3>Recommended Sectors</h3>
            <p>{selectedReport.portfolio_result.recommended_sectors.join(", ")}</p>

            <h3>Recommended Stocks</h3>
            <p>{selectedReport.portfolio_result.recommended_stocks.join(", ")}</p>

            <p><em>{selectedReport.portfolio_result.investment_advice}</em></p>
          </div>
        )}
      </div>
    </div>
  );
}