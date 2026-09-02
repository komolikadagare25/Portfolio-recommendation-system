import React from "react";
import { riskProfile as defaultRiskProfile } from "../../../data/dashboardMock";
import "./RiskProfileBanner.css";

const BAND_CLASS = {
  Low: "risk-banner--low",
  Medium: "risk-banner--medium",
  High: "risk-banner--high",
};

export default function RiskProfileBanner({
  band,
  lastAssessed,
  modelVersion,
  confidence,
  isLoading = false,
}) {
  if (isLoading) {
    return (
      <div className="risk-banner risk-banner--loading">
        <div>
          <span className="dsb-skeleton" style={{ width: "140px", height: "22px", marginBottom: "14px", borderRadius: "20px" }} />
          <span className="dsb-skeleton" style={{ width: "160px", height: "26px", marginBottom: "8px" }} />
          <span className="dsb-skeleton" style={{ width: "180px", height: "12px" }} />
        </div>
        <span className="dsb-skeleton" style={{ width: "70px", height: "30px" }} />
      </div>
    );
  }

  // Use passed values if available,
  // otherwise use the mock data
  const profile = {
    ...defaultRiskProfile,
    ...(band !== undefined && { band }),
    ...(lastAssessed !== undefined && { lastAssessed }),
    ...(modelVersion !== undefined && { modelVersion }),
    ...(confidence !== undefined && { confidence }),
  };

  // The banner's own background reflects the risk band, echoing the same
  // red/green language used for amounts elsewhere on the dashboard.
  const bandClass = BAND_CLASS[profile.band] || "risk-banner--medium";

  return (
    <div className={`risk-banner ${bandClass}`}>
      <div>
        <span className="risk-banner__badge">
          <span className="risk-banner__badge-dot" />
          YOUR RISK PROFILE
        </span>

        <p className="risk-banner__band">
          {profile.band}
        </p>

        <p className="risk-banner__meta">
          Last assessed: {profile.lastAssessed}
          {modelVersion ? ` · Model ${modelVersion}` : ""}
        </p>
      </div>

      <div className="risk-banner__confidence">
        <p className="risk-banner__confidence-value">
          {profile.confidence}%
        </p>

        <p className="risk-banner__confidence-label">
          ML Confidence
        </p>
      </div>
    </div>
  );
}
