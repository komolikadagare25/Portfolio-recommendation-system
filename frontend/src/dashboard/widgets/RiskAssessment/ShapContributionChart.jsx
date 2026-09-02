import React from "react";
import "./ShapContributionChart.css";

/**
 * @param {{ features: Array<{ feature: string, value: number }> }} props
 */
export default function ShapContributionChart({ features }) {
  const maxAbs = Math.max(...features.map((f) => Math.abs(f.value)));

  return (
    <div className="shap-chart">
      {features.map((f, i) => {
        const widthPct = (Math.abs(f.value) / maxAbs) * 100;
        const positive = f.value >= 0;
        return (
          <div key={f.feature} className="shap-chart__row" style={{ "--dsb-stagger": i }}>
            <span className="shap-chart__label">{f.feature}</span>
            <div className="shap-chart__track">
              <div className="shap-chart__zero-line" />
              {positive ? (
                <div className="shap-chart__bar-half shap-chart__bar-half--right">
                  <div className="shap-chart__bar shap-chart__bar--pos" style={{ "--dsb-bar-width": `${widthPct}%` }} />
                </div>
              ) : (
                <div className="shap-chart__bar-half shap-chart__bar-half--left">
                  <div className="shap-chart__bar shap-chart__bar--neg" style={{ "--dsb-bar-width": `${widthPct}%` }} />
                </div>
              )}
            </div>
          </div>
        );
      })}
      <div className="shap-chart__axis-label">SHAP value (impact on model output)</div>
    </div>
  );
}
