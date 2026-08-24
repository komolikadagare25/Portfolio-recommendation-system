import React, { useEffect, useState } from "react";
import RiskProfileBanner from "../../dashboard/widgets/DashboardHome/RiskProfileBanner";
import AllocationDonut from "../../dashboard/widgets/DashboardHome/AllocationDonut";
import ShapFeatureImportance from "../../dashboard/widgets/DashboardHome/ShapFeatureImportance";
import "./DashboardHome.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const ALLOCATION_COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6", "#14b8a6", "#ef4444"];

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

  if (loading) return <div className="dashboard-home"><p>Loading...</p></div>;
  if (error) return <div className="dashboard-home"><p style={{ color: "red" }}>{error}</p></div>;

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

  return (
    <div className="dashboard-home">
      <RiskProfileBanner
        band={`${report.risk_level} Risk`}
        lastAssessed={new Date(report.created_at).toLocaleDateString()}
        confidence={(parseFloat(report.confidence) * 100).toFixed(1)}
      />

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
            <div>
              <button
                onClick={() => setShapLimeTab("SHAP")}
                style={{ fontWeight: shapLimeTab === "SHAP" ? 700 : 400, marginRight: 8 }}
              >
                SHAP
              </button>
              <button
                onClick={() => setShapLimeTab("LIME")}
                style={{ fontWeight: shapLimeTab === "LIME" ? 700 : 400 }}
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
        <p><strong>Sectors:</strong> {report.portfolio_result.recommended_sectors.join(", ")}</p>
        <p><strong>Stocks:</strong> {report.portfolio_result.recommended_stocks.join(", ")}</p>
        <p><em>{report.portfolio_result.investment_advice}</em></p>
      </div>
    </div>
  );
}
