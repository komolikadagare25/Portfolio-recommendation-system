import React from "react";
import { shapFeatures as defaultFeatures } from "../../../data/dashboardMock";
import "./ShapFeatureImportance.css";

// SHAP contribution:
// Positive = feature increases the risk score
// Negative = feature decreases the risk score

export default function ShapFeatureImportance({
  features = defaultFeatures,
}) {
  // Make sure features is always a valid array
  const safeFeatures = Array.isArray(features) ? features : defaultFeatures;

  // Handle empty data safely
  if (!safeFeatures || safeFeatures.length === 0) {
    return (
      <div className="shap-list">
        <p>No feature importance data available.</p>
      </div>
    );
  }

  // Find the largest absolute SHAP value
  const maxAbs = Math.max(
    ...safeFeatures.map((f) => Math.abs(Number(f?.value || 0)))
  );

  return (
    <ul className="shap-list">
      {safeFeatures.map((f, index) => {
        const value = Number(f?.value || 0);

        // Prevent division by zero
        const widthPct =
          maxAbs > 0 ? (Math.abs(value) / maxAbs) * 100 : 0;

        const positive = value >= 0;

        return (
          <li
            key={f?.name || `feature-${index}`}
            className="shap-list__row"
          >
            <span className="shap-list__name">
              {f?.name || "Unknown Feature"}
            </span>

            <span className="shap-list__bar-track">
              <span
                className={`shap-list__bar ${
                  positive
                    ? "shap-list__bar--pos"
                    : "shap-list__bar--neg"
                }`}
                style={{ width: `${widthPct}%` }}
              />
            </span>

            <span
              className={`shap-list__value ${
                positive
                  ? "shap-list__value--pos"
                  : "shap-list__value--neg"
              }`}
            >
              {positive ? "+" : ""}
              {value.toFixed(2)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}