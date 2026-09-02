import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ClipboardList, ArrowRight, Wallet } from "lucide-react";
import "./MyPortfolio.css";
import HistoricalPerformanceChart from "../../dashboard/widgets/DashboardHome/HistoricalPerformanceChart";

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

  if (loading) {
    return (
      <div className="myPortfolio-page">
        <h1>My Portfolio</h1>
        <div className="myPortfolio-panel">
          <span className="dsb-skeleton" style={{ width: "180px", height: "16px", marginBottom: "12px" }} />
          <span className="dsb-skeleton" style={{ width: "90%", height: "12px" }} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="myPortfolio-page">
        <h1>My Portfolio</h1>
        <p className="myPortfolio-page__error">{error}</p>
      </div>
    );
  }

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

      <section className="myPortfolio-panel">
        <h2 className="myPortfolio-panel__title">Asset Allocation</h2>
        <ul className="myPortfolio-allocation-list">
          {Object.entries(portfolio_result.asset_allocation).map(([k, v]) => (
            <li key={k} className="myPortfolio-allocation-row">
              <span>{k}</span>
              <div className="myPortfolio-allocation-row__track">
                <span className="myPortfolio-allocation-row__fill" style={{ width: `${v}%` }} />
              </div>
              <span className="myPortfolio-allocation-row__value">{v}%</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="myPortfolio-panel">
        <h2 className="myPortfolio-panel__title">Recommended Sectors</h2>
        <ul className="myPortfolio-chip-list">
          {portfolio_result.recommended_sectors.map((s) => (
            <li key={s} className="myPortfolio-chip">{s}</li>
          ))}
        </ul>

        <h2 className="myPortfolio-panel__title" style={{ marginTop: "22px" }}>Recommended Stocks</h2>
        <ul className="myPortfolio-chip-list">
          {portfolio_result.recommended_stocks.map((s) => (
            <li key={s} className="myPortfolio-chip myPortfolio-chip--alt">{s}</li>
          ))}
        </ul>

        <p className="myPortfolio-advice">{portfolio_result.investment_advice}</p>
      </section>

      <section className="myPortfolio-panel">
        <h2 className="myPortfolio-panel__title">Historical Performance</h2>
        <HistoricalPerformanceChart reportId={report.id} amount={plan ? plan.total_amount : 10000} riskLevel={report.risk_level} />
      </section>

      <section className="myPortfolio-panel">
        <h2 className="myPortfolio-panel__title">Build Your Portfolio</h2>
        <p className="myPortfolio-panel__subtext">
          Enter an amount to see exactly how many shares of each recommended stock you could buy today, at live market prices.
        </p>

        <div className="myPortfolio-plan-form">
          <div className="myPortfolio-plan-form__input-wrap">
            <Wallet size={15} strokeWidth={1.9} className="myPortfolio-plan-form__icon" />
            <input
              type="number"
              placeholder="e.g. 100000"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="myPortfolio-plan-form__input"
            />
          </div>
          <button
            onClick={handleBuildPlan}
            disabled={planLoading}
            className="myPortfolio-plan-form__btn"
          >
            {planLoading ? "Fetching live prices…" : "Build Plan"}
          </button>
        </div>

        {planError && <p className="myPortfolio-page__error">{planError}</p>}

        {plan && (
          <div className="myPortfolio-plan-result">
            <h3 className="myPortfolio-panel__title">Category Breakdown</h3>
            <ul className="myPortfolio-breakdown-list">
              {plan.category_breakdown.map((c) => (
                <li key={c.category} className="myPortfolio-breakdown-row">
                  <strong>{c.category}: ₹{c.amount.toLocaleString("en-IN")}</strong>
                  {c.guidance && <p>{c.guidance}</p>}
                </li>
              ))}
            </ul>

            <h3 className="myPortfolio-panel__title" style={{ marginTop: "20px" }}>Stock Purchase Plan</h3>
            <table className="myPortfolio-plan-table">
              <thead>
                <tr>
                  <th>Stock</th>
                  <th>Price</th>
                  <th>Shares</th>
                  <th>Invested</th>
                  <th>Leftover</th>
                </tr>
              </thead>
              <tbody>
                {plan.stock_plan.map((s) => (
                  <tr key={s.stock}>
                    <td>{s.stock}</td>
                    <td>{s.price ? `₹${s.price}` : "—"}</td>
                    <td>{s.shares ?? "—"}</td>
                    <td>{s.invested_amount ? `₹${s.invested_amount.toLocaleString("en-IN")}` : "—"}</td>
                    <td>{s.leftover ? `₹${s.leftover.toLocaleString("en-IN")}` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
