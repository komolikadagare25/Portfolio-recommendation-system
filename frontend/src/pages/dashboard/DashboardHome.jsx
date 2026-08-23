import React from "react";
import { Link } from "react-router-dom";
import RiskProfileBanner from "../../dashboard/widgets/DashboardHome/RiskProfileBanner";
import StatCard from "../../dashboard/widgets/DashboardHome/StatCard";
import AllocationDonut from "../../dashboard/widgets/DashboardHome/AllocationDonut";
import ShapFeatureImportance from "../../dashboard/widgets/DashboardHome/ShapFeatureImportance";
import RecommendedStocksTable from "../../dashboard/widgets/DashboardHome/RecommendedStocksTable";
import { riskProfile, stats, allocation, shapFeatures, recommendedStocks } from "../../data/dashboardMock";
import "./DashboardHome.css";

export default function DashboardHome() {
  return (
    <div className="dashboard-home">
      <RiskProfileBanner {...riskProfile} />

      <div className="dashboard-home__stats">
        {stats.map((s) => (
          <StatCard key={s.label} {...s} />
        ))}
      </div>

      <div className="dashboard-home__panels">
        <div className="dashboard-panel">
          <div className="dashboard-panel__header">
            <p className="dashboard-panel__title">Portfolio Allocation</p>
            <Link to="/dashboard/portfolio" className="dashboard-panel__link">
              View full →
            </Link>
          </div>
          <AllocationDonut data={allocation} centerLabel={riskProfile.band.replace(" Risk", "\nRisk")} />
        </div>

        <div className="dashboard-panel">
          <div className="dashboard-panel__header">
            <p className="dashboard-panel__title">SHAP Feature Importance</p>
          </div>
          <ShapFeatureImportance features={shapFeatures} />
        </div>
      </div>

      <div className="dashboard-panel">
        <div className="dashboard-panel__header">
          <p className="dashboard-panel__title">Recommended Stocks</p>
          <Link to="/dashboard/recommendations" className="dashboard-panel__link">
            View all 12 →
          </Link>
        </div>
        <RecommendedStocksTable stocks={recommendedStocks} />
      </div>
    </div>
  );
}
