import React from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import "./DashboardLayout.css";
import RiskProfileBanner from "../widgets/DashboardHome/RiskProfileBanner";
import StatCard from "../widgets/DashboardHome/StatCard";
import AllocationDonut from "../widgets/DashboardHome/AllocationDonut";
import ShapeFeatureImportance from "../widgets/DashboardHome/ShapFeatureImportance";
import RecommendedStocks from "../widgets/DashboardHome/RecommendedStocksTable";

/**
 * Wraps every /dashboard/* route. The matched child page renders via <Outlet />.
 */
export default function DashboardLayout() {
  return (
    <div className="dsb-shell">
      <Sidebar />

      <div className="dsb-main">
        <Topbar />

        <div className="dsb-main__content">

          <Outlet />

        </div>
      </div>
    </div>
  );
}