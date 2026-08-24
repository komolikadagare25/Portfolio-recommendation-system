import React from "react";
import { riskProfile as defaultRiskProfile } from "../../../data/dashboardMock";
import "./RiskProfileBanner.css";

export default function RiskProfileBanner({
  band,
  lastAssessed,
  modelVersion,
  confidence,
}) {
  // Use passed values if available,
  // otherwise use the mock data
  const profile = {
    ...defaultRiskProfile,
    ...(band !== undefined && { band }),
    ...(lastAssessed !== undefined && { lastAssessed }),
    ...(modelVersion !== undefined && { modelVersion }),
    ...(confidence !== undefined && { confidence }),
  };

  return (
    <div className="risk-banner">
      <div>
        <span className="risk-banner__badge">
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