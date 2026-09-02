import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import RiskProfileBanner from "../widgets/DashboardHome/RiskProfileBanner";
import StatCard from "../widgets/DashboardHome/StatCard";
import AllocationDonut from "../widgets/DashboardHome/AllocationDonut";
import ShapFeatureImportance from "../widgets/DashboardHome/ShapFeatureImportance";
import RecommendedStocksTable from "../widgets/DashboardHome/RecommendedStocksTable";
import {
  riskProfile as defaultRiskProfile,
  statCards as defaultStatCards,
  allocation as defaultAllocation,
  shapFeatures as defaultShapFeatures,
  recommendedStocks as defaultStocks,
} from "../../data/dashboardMock";
import "./PageShell.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

/**
 * /dashboard — the landing overview: risk profile banner, key stats,
 * allocation, SHAP drivers, and top recommended stocks. Pulls
 * GET /dashboard/summary from the backend and falls back to bundled mock
 * data per-section if a field is missing, same pattern the widgets
 * already use individually.
 */
export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const token = localStorage.getItem("access_token");

    async function load() {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE_URL}/dashboard/summary`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Failed to load dashboard (${res.status})`);
        const data = await res.json();
        if (!cancelled) {
          setSummary(data);
          setUsingFallback(false);
        }
      } catch (err) {
        if (!cancelled) setUsingFallback(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  const riskProfile = summary?.riskProfile || defaultRiskProfile;
  const stats = summary?.statCards || defaultStatCards;
  const allocation = summary?.allocation || defaultAllocation;
  const shapFeatures = summary?.shapFeatures || defaultShapFeatures;
  const stocks = summary?.recommendedStocks || defaultStocks;

  return (
    <div className="page-shell">
      {usingFallback && !loading && (
        <p className="page-shell__notice">
          Showing sample data — couldn't reach the dashboard service.
        </p>
      )}

      <RiskProfileBanner
        band={riskProfile.band}
        lastAssessed={riskProfile.lastAssessed}
        modelVersion={riskProfile.modelVersion}
        confidence={riskProfile.confidence}
        isLoading={loading}
      />

      <div className="page-shell__stat-grid">
        {stats.map((s, i) => (
          <StatCard key={s.label} {...s} isLoading={loading} index={i} />
        ))}
      </div>

      <div className="page-shell__two-col">
        <section className="page-shell__panel">
          <div className="page-shell__panel-header">
            <h2 className="page-shell__panel-title" style={{ margin: 0 }}>Portfolio Allocation</h2>
            <Link to="/dashboard/portfolio" className="page-shell__panel-link">View full →</Link>
          </div>
          <AllocationDonut data={allocation} isLoading={loading} />
        </section>

        <section className="page-shell__panel">
          <h2 className="page-shell__panel-title">SHAP Feature Importance</h2>
          <ShapFeatureImportance features={shapFeatures} isLoading={loading} />
        </section>
      </div>

      <section className="page-shell__panel">
        <div className="page-shell__panel-header">
          <h2 className="page-shell__panel-title" style={{ margin: 0 }}>Recommended Stocks</h2>
          <Link to="/dashboard/recommendations" className="page-shell__panel-link">View all {stocks.length > 4 ? stocks.length : 12} →</Link>
        </div>
        <RecommendedStocksTable stocks={stocks.slice(0, 4)} isLoading={loading} />
      </section>
    </div>
  );
}
