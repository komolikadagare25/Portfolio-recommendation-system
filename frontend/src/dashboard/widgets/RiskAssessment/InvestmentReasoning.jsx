import React, { useEffect, useState } from "react";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const VOLATILITY_COLOR = { Low: "#22c55e", Moderate: "#f59e0b", High: "#ef4444" };
const CHARACTER_LABEL = { steadier: "Steadier", moderate: "Moderate", growth: "Growth" };
const CHARACTER_COLOR = { steadier: "#22c55e", moderate: "#f59e0b", growth: "#3b82f6" };

export default function InvestmentReasoning({ reportId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const token = localStorage.getItem("access_token");

  useEffect(() => {
    if (!reportId) return;
    async function load() {
      try {
        const res = await fetch(`${API_BASE_URL}/reports/${reportId}/investment-reasoning`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Failed to load (${res.status})`);
        setData(await res.json());
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [reportId, token]);

  if (loading) return <p>Loading reasoning...</p>;
  if (error) return <p style={{ color: "red" }}>{error}</p>;
  if (!data) return null;

  return (
    <div>
      <h3>Why these sectors</h3>
      {data.sectors.map((s) => (
        <div key={s.sector} style={{ marginBottom: "10px" }}>
          <strong>{s.sector}</strong>
          {s.character && (
            <span
              style={{
                marginLeft: "8px",
                fontSize: "0.75em",
                fontWeight: 700,
                padding: "1px 8px",
                borderRadius: "10px",
                background: `${CHARACTER_COLOR[s.character]}22`,
                color: CHARACTER_COLOR[s.character],
              }}
            >
              {CHARACTER_LABEL[s.character]}
            </span>
          )}
          <p style={{ margin: "2px 0 0", fontSize: "0.9em", color: "#555" }}>{s.explanation}</p>
        </div>
      ))}

      <h3>Why these stocks</h3>
      {data.stocks.map((s) => (
        <div key={s.stock} style={{ marginBottom: "10px" }}>
          <strong>{s.stock}</strong>
          {s.volatility_label && (
            <span
              style={{
                marginLeft: "8px",
                fontSize: "0.75em",
                fontWeight: 700,
                padding: "1px 8px",
                borderRadius: "10px",
                background: `${VOLATILITY_COLOR[s.volatility_label]}22`,
                color: VOLATILITY_COLOR[s.volatility_label],
              }}
            >
              {s.volatility_label} volatility
            </span>
          )}
          <p style={{ margin: "2px 0 0", fontSize: "0.9em", color: "#555" }}>{s.explanation}</p>
        </div>
      ))}
    </div>
  );
}