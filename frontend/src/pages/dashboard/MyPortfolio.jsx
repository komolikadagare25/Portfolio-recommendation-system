import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardList, ArrowRight } from "lucide-react";
import "./MyPortfolio.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

export default function MyPortfolio() {
  const [report, setReport] = useState(null);
  const [amount, setAmount] = useState("");
  const [plan, setPlan] = useState(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [planError, setPlanError] = useState(null);
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

    const handleBuildPlan = async () => {
    setPlanError(null);
    setPlan(null);

    const numericAmount = parseFloat(amount);
    if (!numericAmount || numericAmount <= 0) {
      setPlanError("Enter a valid amount greater than 0");
      return;
    }

    setPlanLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/reports/${report.id}/investment-plan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ amount: numericAmount }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Failed (${res.status})`);
      }
      setPlan(await res.json());
    } catch (err) {
      setPlanError(err.message);
    } finally {
      setPlanLoading(false);
    }
  };

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

      <h2>Build Your Portfolio</h2>
      <p>Enter an amount to see exactly how many shares of each recommended stock you could buy today, at live market prices.</p>

      <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
        <input
          type="number"
          placeholder="e.g. 100000"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          style={{ padding: "8px", border: "1px solid #ccc", borderRadius: "6px", width: "200px" }}
        />
        <button
          onClick={handleBuildPlan}
          disabled={planLoading}
          style={{ padding: "8px 16px", borderRadius: "6px", border: "none", background: "#3b82f6", color: "#fff", cursor: "pointer" }}
        >
          {planLoading ? "Fetching live prices..." : "Build Plan"}
        </button>
      </div>

      {planError && <p style={{ color: "red" }}>{planError}</p>}

      {plan && (
        <div style={{ border: "1px solid #ddd", borderRadius: "8px", padding: "16px" }}>
                    <h3>Category Breakdown</h3>
          <ul style={{ listStyle: "none", padding: 0 }}>
            {plan.category_breakdown.map((c) => (
              <li key={c.category} style={{ marginBottom: "10px" }}>
                <strong>{c.category}: ₹{c.amount.toLocaleString()}</strong>
                {c.guidance && (
                  <p style={{ margin: "2px 0 0", fontSize: "0.85em", color: "#666" }}>{c.guidance}</p>
                )}
              </li>
            ))}
          </ul>

          <h3>Stock Purchase Plan</h3>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>
                <th style={{ padding: "6px" }}>Stock</th>
                <th style={{ padding: "6px" }}>Price</th>
                <th style={{ padding: "6px" }}>Shares</th>
                <th style={{ padding: "6px" }}>Invested</th>
                <th style={{ padding: "6px" }}>Leftover</th>
              </tr>
            </thead>
            <tbody>
              {plan.stock_plan.map((s) => (
                <tr key={s.stock} style={{ borderBottom: "1px solid #f0f0f0" }}>
                  <td style={{ padding: "6px" }}>{s.stock}</td>
                  <td style={{ padding: "6px" }}>{s.price ? `₹${s.price}` : "—"}</td>
                  <td style={{ padding: "6px" }}>{s.shares ?? "—"}</td>
                  <td style={{ padding: "6px" }}>{s.invested_amount ? `₹${s.invested_amount.toLocaleString()}` : "—"}</td>
                  <td style={{ padding: "6px" }}>{s.leftover ? `₹${s.leftover.toLocaleString()}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}