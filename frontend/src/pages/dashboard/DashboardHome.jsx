import React, { useEffect, useState } from "react";
import RiskProfileBanner from "../../dashboard/widgets/DashboardHome/RiskProfileBanner";
import StatCard from "../../dashboard/widgets/DashboardHome/StatCard";
import AllocationDonut from "../../dashboard/widgets/DashboardHome/AllocationDonut";
import ShapFeatureImportance from "../../dashboard/widgets/DashboardHome/ShapFeatureImportance";
import "./DashboardHome.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const ALLOCATION_COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6", "#14b8a6", "#ef4444"];

const RISK_TONE = {
  low: "up", conservative: "up",
  medium: "warn", moderate: "warn",
  high: "down", aggressive: "down",
};

function toneForRisk(riskLevel) {
  return RISK_TONE[String(riskLevel || "").toLowerCase()] || "neutral";
}

function toneForConfidence(pct) {
  if (pct >= 70) return "up";
  if (pct >= 40) return "warn";
  return "down";
}

function prettifyFeatureName(name) {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function DashboardHome() {
  const [report, setReport] = useState(null);
  const [shapLimeTab, setShapLimeTab] = useState("SHAP");
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

        const latestId = reports[0].id; // already sorted newest-first by the backend
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

  if (loading) {
    return (
      <div className="dashboard-home">
        <div className="dashboard-panel">
          <span className="dsb-skeleton" style={{ width: "160px", height: "16px", marginBottom: "12px" }} />
          <span className="dsb-skeleton" style={{ width: "90%", height: "12px" }} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-home">
        <p className="dashboard-home__error">{error}</p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="dashboard-home">
        <p>No reports yet — complete a Risk Assessment to see your dashboard.</p>
      </div>
    );
  }

  const allocationData = Object.entries(report.portfolio_result.asset_allocation).map(
    ([label, value], i) => ({ label, value, color: ALLOCATION_COLORS[i % ALLOCATION_COLORS.length] })
  );

  const shapFeatures = [
    ...report.shap_result.top_positive_features,
    ...report.shap_result.top_negative_features,
  ]
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))
    .map((f) => ({ name: prettifyFeatureName(f.feature), value: f.impact }));

  const limeFeatures = report.lime_result.top_features.map((f) => ({
    name: prettifyFeatureName(f.feature),
    value: f.weight,
  }));

  const confidencePct = (parseFloat(report.confidence) * 100).toFixed(1);
  const sectorCount = report.portfolio_result.recommended_sectors.length;
  const stockCount = report.portfolio_result.recommended_stocks.length;

  return (
    <div className="dashboard-home">
      <RiskProfileBanner
        band={report.risk_level}
        lastAssessed={new Date(report.created_at).toLocaleDateString()}
        confidence={confidencePct}
      />

      <div className="dashboard-home__stats">
        <StatCard label="RISK LEVEL" value={report.risk_level} caption="Current classification" tone={toneForRisk(report.risk_level)} index={0} />
        <StatCard label="MODEL CONFIDENCE" value={`${confidencePct}%`} caption="In this classification" tone={toneForConfidence(parseFloat(confidencePct))} index={1} />
        <StatCard label="RECOMMENDED SECTORS" value={String(sectorCount)} caption="Across your allocation" tone="info" index={2} />
        <StatCard label="RECOMMENDED STOCKS" value={String(stockCount)} caption="Matched to your profile" tone="info" index={3} />
      </div>

      <div className="dashboard-home__panels">
        <div className="dashboard-panel">
          <div className="dashboard-panel__header">
            <p className="dashboard-panel__title">Portfolio Allocation</p>
          </div>
          <AllocationDonut data={allocationData} centerLabel={`${report.risk_level}\nRisk`} />
        </div>

        <div className="dashboard-panel">
          <div className="dashboard-panel__header">
            <p className="dashboard-panel__title">
              {shapLimeTab === "SHAP" ? "SHAP Feature Importance" : "LIME Feature Weights"}
            </p>
            <div className="dashboard-panel__toggle-group">
              <button
                className={`dashboard-panel__toggle-btn ${shapLimeTab === "SHAP" ? "dashboard-panel__toggle-btn--active" : ""}`}
                onClick={() => setShapLimeTab("SHAP")}
              >
                SHAP
              </button>
              <button
                className={`dashboard-panel__toggle-btn ${shapLimeTab === "LIME" ? "dashboard-panel__toggle-btn--active" : ""}`}
                onClick={() => setShapLimeTab("LIME")}
              >
                LIME
              </button>
            </div>
          </div>
          {shapLimeTab === "SHAP" ? (
            <ShapFeatureImportance features={shapFeatures} />
          ) : (
            <ShapFeatureImportance features={limeFeatures} />
          )}
        </div>
      </div>

      <div className="dashboard-panel">
        <div className="dashboard-panel__header">
          <p className="dashboard-panel__title">Recommended Sectors &amp; Stocks</p>
        </div>
        <div className="dashboard-home__chip-row">
          <span className="dashboard-home__chip-label">Sectors</span>
          {report.portfolio_result.recommended_sectors.map((s) => (
            <span key={s} className="dashboard-home__chip">{s}</span>
          ))}
        </div>
        <div className="dashboard-home__chip-row">
          <span className="dashboard-home__chip-label">Stocks</span>
          {report.portfolio_result.recommended_stocks.map((s) => (
            <span key={s} className="dashboard-home__chip dashboard-home__chip--alt">{s}</span>
          ))}
        </div>
        <p className="dashboard-home__advice">{report.portfolio_result.investment_advice}</p>
      </div>
    </div>
  );
}
