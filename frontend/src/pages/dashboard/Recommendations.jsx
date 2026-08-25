import React from "react";
import RecommendationsExplorer from "../../dashboard/widgets/Recommendations/RecommendationsExplorer";
import { recommendedStocks } from "../../data/recommendationsMock";
import "./Recommendations.css";

/**
 * TODO: once your backend exists, fetch the real recommendation list (and
 * per-stock SHAP/LIME reasons) here instead of importing recommendationsMock.
 */
export default function Recommendations() {
  return (
    <div className="recommendations-page">
      <h1>Recommendations</h1>
      <p>
        Your full recommended stock list, based on your latest risk assessment.
        Filter by sector, risk level, or expected return, and expand any row
        to see why it was recommended.
      </p>

      <RecommendationsExplorer stocks={recommendedStocks} />
    </div>
  );
}
