import React, { useEffect, useState } from "react";
import StatCard from "../widgets/DashboardHome/StatCard";
import AllocationDonut from "../widgets/DashboardHome/AllocationDonut";
import PortfolioHoldingsTable from "../widgets/MyPortfolio/PortfolioHoldingsTable";
import { portfolioSummary as defaultSummary, portfolioHoldings as defaultHoldings } from "../../data/dashboardMock";
import "./PageShell.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const SECTOR_COLORS = {
  Technology: "#3b82f6",
  Banking: "#d97706",
  FMCG: "#16a34a",
  Infra: "#0891b2",
  Pharma: "#8b5cf6",
};

const fmtRupee = (v) => `₹${Number(v || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

/**
 * /dashboard/portfolio — the user's actual current holdings, as opposed to
 * the model's suggestions (that's the Recommendations page). Pulls from
 * GET /portfolio on the backend; falls back to bundled mock data so the
 * page still renders something sensible if that endpoint isn't reachable.
 */
export default function MyPortfolioPage() {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const token = localStorage.getItem("access_token");

    async function load() {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE_URL}/portfolio`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Failed to load portfolio (${res.status})`);
        const data = await res.json();
        if (!cancelled) {
          setPortfolio(data);
          setUsingFallback(false);
        }
      } catch (err) {
        if (!cancelled) {
          setPortfolio({ summary: defaultSummary, holdings: defaultHoldings });
          setUsingFallback(true);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  const summary = portfolio?.summary || defaultSummary;
  const holdings = portfolio?.holdings || defaultHoldings;

  const sectorTotals = holdings.reduce((acc, h) => {
    const value = Number(h.qty || 0) * Number(h.ltp || 0);
    acc[h.sector] = (acc[h.sector] || 0) + value;
    return acc;
  }, {});
  const totalValue = Object.values(sectorTotals).reduce((a, b) => a + b, 0) || 1;
  const allocationFromHoldings = Object.entries(sectorTotals).map(([label, value]) => ({
    label,
    value: Math.round((value / totalValue) * 100),
    color: SECTOR_COLORS[label] || "#94a3b8",
  }));

  const gaining = summary.totalGain >= 0;
  const todayGaining = summary.todayChange >= 0;

  return (
    <div className="page-shell">
      <div className="page-shell__header">
        <div>
          <h1>My Portfolio</h1>
          <p>Your actual holdings and how they're performing right now.</p>
        </div>
      </div>

      {usingFallback && !loading && (
        <p className="page-shell__notice">
          Showing sample data — couldn't reach the portfolio service.
        </p>
      )}

      <div className="page-shell__stat-grid">
        <StatCard label="TOTAL VALUE" value={loading ? "" : fmtRupee(summary.totalValue)} caption={loading ? "" : `Invested ${fmtRupee(summary.investedValue)}`} tone="neutral" isLoading={loading} index={0} />
        <StatCard label="TOTAL P&L" value={loading ? "" : `${gaining ? "+" : ""}${fmtRupee(summary.totalGain)}`} caption={loading ? "" : `${gaining ? "+" : ""}${summary.totalGainPct}% overall`} tone={gaining ? "up" : "down"} isLoading={loading} index={1} />
        <StatCard label="TODAY'S CHANGE" value={loading ? "" : `${todayGaining ? "+" : ""}${fmtRupee(summary.todayChange)}`} caption={loading ? "" : `${todayGaining ? "+" : ""}${summary.todayChangePct}% today`} tone={todayGaining ? "up" : "down"} isLoading={loading} index={2} />
        <StatCard label="XIRR" value={loading ? "" : `${summary.xirr}%`} caption="Since inception" tone="up" isLoading={loading} index={3} />
      </div>

      <div className="page-shell__two-col">
        <section className="page-shell__panel page-shell__panel--wide">
          <h2 className="page-shell__panel-title">Holdings</h2>
          <PortfolioHoldingsTable holdings={holdings} isLoading={loading} />
        </section>

        <section className="page-shell__panel">
          <h2 className="page-shell__panel-title">Allocation by Sector</h2>
          <AllocationDonut data={allocationFromHoldings} centerLabel={"Your\nPortfolio"} isLoading={loading} />
        </section>
      </div>
    </div>
  );
}
