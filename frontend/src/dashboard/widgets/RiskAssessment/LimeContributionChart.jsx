import React from "react";
import "./LimeContributionChart.css";

/**
 * @param {{ features: Array<{ feature: string, weight: number }> }} props
 */
export default function LimeContributionChart({ features }) {
  const maxAbs = Math.max(...features.map((f) => Math.abs(f.weight)));

  return (
    <div className="lime-chart">
      {features.map((f, i) => {
        const widthPct = (Math.abs(f.weight) / maxAbs) * 100;
        const positive = f.weight >= 0;
        return (
          <div key={f.feature} className="lime-chart__row" style={{ "--dsb-stagger": i }}>
            <span className="lime-chart__label">{f.feature}</span>
            <div className="lime-chart__track">
              <div className="lime-chart__zero-line" />
              {positive ? (
                <div className="lime-chart__bar-half lime-chart__bar-half--right">
                  <div className="lime-chart__bar lime-chart__bar--pos" style={{ "--dsb-bar-width": `${widthPct}%` }} />
                </div>
              ) : (
                <div className="lime-chart__bar-half lime-chart__bar-half--left">
                  <div className="lime-chart__bar lime-chart__bar--neg" style={{ "--dsb-bar-width": `${widthPct}%` }} />
                </div>
              )}
            </div>
          </div>
        );
      })}
      <div className="lime-chart__axis-label">LIME weight (local linear model coefficient)</div>
    </div>
  );
}
