import React from "react";
import { Link } from "react-router-dom";
import { ClipboardList, ArrowRight } from "lucide-react";
import { usePortfolio } from "../../context/PortfolioContext";
import RiskResultTabs from "../../dashboard/widgets/RiskAssessment/RiskResultTabs";
import "./MyPortfolio.css";

/**
 * Route: /dashboard/portfolio
 *
 * This is where the ML result lands right after the Risk Assessment
 * questionnaire: RiskAssessment.jsx stores the API response
 * ({ prediction, portfolio, shap, lime }) in PortfolioContext and redirects
 * here, and this page renders it with the same RiskResultTabs component
 * (Prediction & Portfolio / SHAP / LIME / AI Decision Summary) used during
 * the assessment flow -- so the layout matches the Streamlit reference 1:1.
 *
 * If no assessment has been completed yet (fresh session, cleared storage),
 * `result` is null and we show an empty state pointing at the assessment
 * instead of silently falling back to mock data, so it's obvious this page
 * is showing real personalized output, not a placeholder.
 */
export default function MyPortfolio() {
  const { result } = usePortfolio();

  if (!result) {
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

  return (
    <div className="myPortfolio-page">
      <h1>My Portfolio</h1>
      <p>Based on your latest risk assessment.</p>

      {result.isMock && (
        <div className="myPortfolio-mock-banner">
          Showing demo data — the prediction backend isn't reachable yet, so
          this is bundled mock data, not a real model output.
        </div>
      )}

      <RiskResultTabs
        prediction={result.prediction}
        portfolio={result.portfolio}
        shap={result.shap}
        lime={result.lime}
      />
    </div>
  );
}
