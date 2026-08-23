import React, { useMemo, useState } from "react";
import { ChevronDown, Brain, Search } from "lucide-react";
import "./RecommendationsExplorer.css";

const SECTOR_COLORS = {
  Technology: "blue",
  Banking: "amber",
  FMCG: "teal",
  Infra: "coral",
  Pharma: "indigo",
};

const RISK_COLORS = {
  Low: "teal",
  Medium: "amber",
  High: "danger",
};

const RETURN_FILTERS = [
  { label: "Any expected return", value: 0 },
  { label: "10%+", value: 10 },
  { label: "15%+", value: 15 },
  { label: "20%+", value: 20 },
];

/**
 * @param {{ stocks: Array<{
 *   symbol: string, name: string, sector: string, weight: number,
 *   expReturn: number, risk: string,
 *   reasons: { shap: string[], lime: string[] }
 * }> }} props
 */
export default function RecommendationsExplorer({ stocks }) {
  const [sector, setSector] = useState("All");
  const [risk, setRisk] = useState("All");
  const [minReturn, setMinReturn] = useState(0);
  const [expanded, setExpanded] = useState(() => new Set());

  const sectors = useMemo(() => ["All", ...new Set(stocks.map((s) => s.sector))], [stocks]);
  const risks = useMemo(() => ["All", ...new Set(stocks.map((s) => s.risk))], [stocks]);

  const filtered = useMemo(
    () =>
      stocks.filter(
        (s) =>
          (sector === "All" || s.sector === sector) &&
          (risk === "All" || s.risk === risk) &&
          s.expReturn >= minReturn
      ),
    [stocks, sector, risk, minReturn]
  );

  const maxWeight = Math.max(...stocks.map((s) => s.weight));

  function toggleRow(symbol) {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(symbol) ? next.delete(symbol) : next.add(symbol);
      return next;
    });
  }

  return (
    <div className="rec-explorer">
      <div className="rec-explorer__filters">
        <label className="rec-explorer__filter">
          <span>Sector</span>
          <select value={sector} onChange={(e) => setSector(e.target.value)}>
            {sectors.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>

        <label className="rec-explorer__filter">
          <span>Risk level</span>
          <select value={risk} onChange={(e) => setRisk(e.target.value)}>
            {risks.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </label>

        <label className="rec-explorer__filter">
          <span>Expected return</span>
          <select value={minReturn} onChange={(e) => setMinReturn(Number(e.target.value))}>
            {RETURN_FILTERS.map((f) => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>
        </label>

        <span className="rec-explorer__count">
          {filtered.length} of {stocks.length} stocks
        </span>
      </div>

      <div className="rec-explorer__list">
        <div className="rec-explorer__head-row">
          <span>Stock</span>
          <span>Sector</span>
          <span>Weight</span>
          <span>Exp. Return</span>
          <span>Risk</span>
          <span />
        </div>

        {filtered.length === 0 && (
          <div className="rec-explorer__empty">
            <Search size={18} strokeWidth={1.75} />
            No stocks match these filters — try widening your criteria.
          </div>
        )}

        {filtered.map((s) => {
          const isOpen = expanded.has(s.symbol);
          return (
            <div key={s.symbol} className={`rec-explorer__row ${isOpen ? "rec-explorer__row--open" : ""}`}>
              <button className="rec-explorer__row-main" onClick={() => toggleRow(s.symbol)}>
                <span className="rec-explorer__stock">
                  <span className="rec-explorer__symbol">{s.symbol}</span>
                  <span className="rec-explorer__name">{s.name}</span>
                </span>

                <span className={`rec-explorer__badge rec-explorer__badge--${SECTOR_COLORS[s.sector] || "gray"}`}>
                  {s.sector}
                </span>

                <span className="rec-explorer__weight">
                  <span className="rec-explorer__weight-track">
                    <span
                      className="rec-explorer__weight-fill"
                      style={{ width: `${(s.weight / maxWeight) * 100}%` }}
                    />
                  </span>
                  <span className="rec-explorer__weight-value">{s.weight}%</span>
                </span>

                <span className="rec-explorer__return">+{s.expReturn}%</span>

                <span className={`rec-explorer__badge rec-explorer__badge--${RISK_COLORS[s.risk] || "gray"}`}>
                  {s.risk}
                </span>

                <ChevronDown
                  size={16}
                  strokeWidth={2}
                  className="rec-explorer__chevron"
                  style={{ transform: isOpen ? "rotate(180deg)" : "rotate(0deg)" }}
                />
              </button>

              {isOpen && (
                <div className="rec-explorer__why">
                  <p className="rec-explorer__why-title">
                    <Brain size={14} strokeWidth={1.75} /> Why {s.symbol} was recommended
                  </p>
                  <div className="rec-explorer__why-cols">
                    <div className="rec-explorer__why-col">
                      <p className="rec-explorer__why-heading">🧠 SHAP</p>
                      <ul>
                        {s.reasons.shap.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="rec-explorer__why-col">
                      <p className="rec-explorer__why-heading">🔍 LIME</p>
                      <ul>
                        {s.reasons.lime.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
