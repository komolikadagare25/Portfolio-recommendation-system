import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";

import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./routes/ProtectedRoute";
import { PortfolioProvider } from "./context/PortfolioContext";

import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Features from "./pages/Features";
import Design from "./pages/SystemDesign";

import DashboardLayout from "./dashboard/layout/DashboardLayout";
import DashboardHome from "./pages/dashboard/DashboardHome";
import RiskAssessment from "./pages/dashboard/RiskAssessment";
import MyPortfolio from "./pages/dashboard/MyPortfolio";
import Recommendations from "./pages/dashboard/Recommendations";
import History from "./pages/dashboard/History";
import Settings from "./pages/dashboard/Settings";
import Help from "./pages/dashboard/Help";

const root = ReactDOM.createRoot(document.getElementById("root"));

root.render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <PortfolioProvider>
          <Routes>

            {/* Public Routes */}
            <Route path="/" element={<Landing />} />
            <Route path="/features" element={<Features />} />
            <Route path="/design" element={<Design />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />

            {/* Protected Dashboard Routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardHome />} />
              <Route
                path="risk-assessment"
                element={<RiskAssessment />}
              />
              <Route
                path="portfolio"
                element={<MyPortfolio />}
              />
              <Route
                path="recommendations"
                element={<Recommendations />}
              />
              <Route
                path="history"
                element={<History />}
              />
              <Route
                path="settings"
                element={<Settings />}
              />
              <Route
                path="help"
                element={<Help />}
              />
            </Route>

          </Routes>
        </PortfolioProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);