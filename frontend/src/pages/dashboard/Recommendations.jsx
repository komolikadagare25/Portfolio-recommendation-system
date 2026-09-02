import React, { useEffect, useState } from "react";
import ShapPlainExplanation from "../../dashboard/widgets/RiskAssessment/ShapPlainExplanation";
import LimePlainExplanation from "../../dashboard/widgets/RiskAssessment/LimePlainExplanation";
import BeginnerGuide from "../../dashboard/widgets/RiskAssessment/BeginnerGuide";
import InvestmentReasoning from "../../dashboard/widgets/RiskAssessment/InvestmentReasoning";
import CollapsibleSection from "../../dashboard/widgets/RiskAssessment/CollapsibleSection";
import "./Recommendations.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

export default function Recommendations() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const token = localStorage.getItem("access_token");

  useEffect(() => {
    async function loadLatestReport() {
      try {
        const listRes = await fetch(`${API_BASE_URL}/reports`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!listRes.ok) throw new Error(`Failed to load reports (${listRes.status})`);
        const reports = await listRes.json();

        if (reports.length === 0) {
          setLoading(false);
          return;
        }

        const detailRes = await fetch(`${API_BASE_URL}/reports/${reports[0].id}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!detailRes.ok) throw new Error(`Failed to load report (${detailRes.status})`);
        setReport(await detailRes.json());
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadLatestReport();
  }, [token]);

  if (loading) {
    return (
      <div className="recommendations-page">
        <h1>Recommendations</h1>
        <div className="recommendations-page__panel">
          <span className="dsb-skeleton" style={{ width: "220px", height: "16px", marginBottom: "12px" }} />
          <span className="dsb-skeleton" style={{ width: "90%", height: "12px", marginBottom: "8px" }} />
          <span className="dsb-skeleton" style={{ width: "70%", height: "12px" }} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="recommendations-page">
        <h1>Recommendations</h1>
        <p className="recommendations-page__error">{error}</p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="recommendations-page">
        <h1>Recommendations</h1>
        <p>No reports yet — complete a Risk Assessment to see recommendations.</p>
      </div>
    );
  }

  const { portfolio_result, shap_result, lime_result, risk_level } = report;

  const shapTopPositive = shap_result.top_positive_features;
  const shapTopNegative = shap_result.top_negative_features;

  // LIME's `feature` string already includes its threshold condition
  // (e.g. "3.00 < equity_market <= 4.00"), so we reuse it as `condition` too.
  const limeFeatures = lime_result.top_features.map((f) => ({
    feature: f.feature,
    condition: f.feature,
    weight: f.weight,
    answer_value: f.answer_value,
  }));
  const limeTopPositive = limeFeatures.filter((f) => f.weight >= 0).sort((a, b) => b.weight - a.weight);
  const limeTopNegative = limeFeatures.filter((f) => f.weight < 0).sort((a, b) => a.weight - b.weight);

  const explanation = portfolio_result.personalization_explanation;

  return (
    <div className="recommendations-page">
      <div className="recommendations-page__header">
        <h1>Recommendations</h1>
        <p className="recommendations-page__subtitle">
          Based on your <strong>{risk_level}</strong> risk profile
          <span className="recommendations-page__confidence-pill">
            confidence {(parseFloat(report.confidence) * 100).toFixed(1)}%
          </span>
        </p>
      </div>

      <section className="recommendations-page__panel">
        <InvestmentReasoning reportId={report.id} />

        <p className="recommendations-page__advice">{portfolio_result.investment_advice}</p>

        <CollapsibleSection title="Show the plain sector/stock lists" defaultOpen={false}>
          <div className="recommendations-page__plain-lists">
            <div>
              <h3>Sectors</h3>
              <ul className="recommendations-page__chip-list">
                {portfolio_result.recommended_sectors.map((s) => (
                  <li key={s} className="recommendations-page__chip">{s}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3>Stocks</h3>
              <ul className="recommendations-page__chip-list">
                {portfolio_result.recommended_stocks.map((s) => (
                  <li key={s} className="recommendations-page__chip">{s}</li>
                ))}
              </ul>
            </div>
          </div>
        </CollapsibleSection>
      </section>

      {explanation && (
        <section className="recommendations-page__panel">
          <h2 className="recommendations-page__panel-title">Why your allocation looks like this</h2>
          <p className="recommendations-page__panel-subtext">{explanation.summary}</p>

          <table className="recommendations-page__table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Standard Template</th>
                <th>Your Allocation</th>
                <th>Change</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(explanation.final_allocation).map(([category, finalVal]) => {
                const baseVal = explanation.base_allocation[category];
                const delta = finalVal - baseVal;
                const deltaClass = delta > 0 ? "dsb-amount--positive" : delta < 0 ? "dsb-amount--negative" : "";
                return (
                  <tr key={category}>
                    <td>{category}</td>
                    <td className="recommendations-page__num">{baseVal}%</td>
                    <td className="recommendations-page__num">{finalVal}%</td>
                    <td className={`recommendations-page__num ${deltaClass}`}>
                      {delta > 0 ? "+" : ""}{delta}pts
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}

      <section className="recommendations-page__panel">
        <CollapsibleSection title="Want the technical detail behind your risk classification?" defaultOpen={false}>
          <p className="recommendations-page__panel-subtext" style={{ marginBottom: "18px" }}>
            This explains how the AI arrived at your {risk_level} risk category —
            a separate, earlier step from the sector/stock reasoning above.
          </p>
          <div className="recommendations-page__explanations">
            <ShapPlainExplanation
              predictedBand={risk_level}
              topPositive={shapTopPositive}
              topNegative={shapTopNegative}
            />
            <LimePlainExplanation
              predictedBand={risk_level}
              topPositive={limeTopPositive}
              topNegative={limeTopNegative}
            />
          </div>
        </CollapsibleSection>
      </section>

      <BeginnerGuide />
    </div>
  );
}
