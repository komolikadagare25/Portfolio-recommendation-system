import React from "react";
import { shapFeatures as defaultFeatures } from "../../../data/dashboardMock";
import "./ShapFeatureImportance.css";

// SHAP contribution:
// Positive = feature increases the risk score  -> colored red (risky)
// Negative = feature decreases the risk score  -> colored green (safe)

export default function ShapFeatureImportance({
  features = defaultFeatures,
  isLoading = false,
}) {
  if (isLoading) {
    return (
      <ul className="shap-list">
        {[0, 1, 2, 3, 4].map((i) => (
          <li key={i} className="shap-list__row">
            <span className="dsb-skeleton" style={{ width: "90px", height: "10px", justifySelf: "end" }} />
            <span className="dsb-skeleton" style={{ width: "100%", height: "8px" }} />
            <span className="dsb-skeleton" style={{ width: "36px", height: "10px" }} />
          </li>
        ))}
      </ul>
    );
  }

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
            style={{ "--dsb-stagger": index }}
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
                style={{ "--dsb-bar-width": `${widthPct}%` }}
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
