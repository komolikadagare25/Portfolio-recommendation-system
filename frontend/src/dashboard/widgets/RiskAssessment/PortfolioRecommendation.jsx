import React from "react";
import CollapsibleSection from "./CollapsibleSection";
import "./PortfolioRecommendation.css";

/**
 * @param {{ portfolio: {
 *   allocation: Array<{ label: string, pct: number }>,
 *   sectors: string[],
 *   stocks: string[],
 *   advice: string
 * } }} props
 */
export default function PortfolioRecommendation({ portfolio }) {
  const { allocation, sectors, stocks, advice } = portfolio;

  return (
    <div className="portfolio-rec">
      <div className="portfolio-rec__header">
        <span className="portfolio-rec__icon">💼</span>
        <h2 className="portfolio-rec__title">Portfolio Recommendation</h2>
      </div>

      <CollapsibleSection icon="✅" title="Asset Allocation">
        <div className="portfolio-rec__allocation-row">
          {allocation.map((a) => (
            <div key={a.label} className="portfolio-rec__allocation-item">
              <p className="portfolio-rec__allocation-label">{a.label}</p>
              <p className="portfolio-rec__allocation-value">{a.pct}%</p>
            </div>
          ))}
        </div>
      </CollapsibleSection>

      <div className="portfolio-rec__two-col">
        <CollapsibleSection icon="🏦" title="Recommended Sectors">
          <ul className="portfolio-rec__list">
            {sectors.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </CollapsibleSection>

        <CollapsibleSection icon="📌" title="Recommended Stocks">
          <ul className="portfolio-rec__list">
            {stocks.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </CollapsibleSection>
      </div>

      <CollapsibleSection icon="💬" title="Investment Advice">
        <p className="portfolio-rec__advice">{advice}</p>
      </CollapsibleSection>
    </div>
  );
}
