import React, { useEffect, useState } from "react";
import "./InvestmentReasoning.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const CHARACTER_LABEL = { steadier: "Steadier", moderate: "Moderate", growth: "Growth" };
const CHARACTER_TONE = { steadier: "teal", moderate: "amber", growth: "blue" };

const VOLATILITY_TONE = { Low: "teal", Moderate: "amber", High: "danger" };

export default function InvestmentReasoning({ reportId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const token = localStorage.getItem("access_token");

  useEffect(() => {
    if (!reportId) return;
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE_URL}/reports/${reportId}/investment-reasoning`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Failed to load (${res.status})`);
        const json = await res.json();
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId]);

  if (loading) {
    return (
      <div className="investment-reasoning">
        <div className="investment-reasoning__block">
          {[0, 1, 2].map((i) => (
            <div key={i} className="investment-reasoning__item">
              <span className="dsb-skeleton" style={{ width: "140px", height: "14px", marginBottom: "8px" }} />
              <span className="dsb-skeleton" style={{ width: "90%", height: "12px" }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) return <p className="investment-reasoning__error">{error}</p>;
  if (!data) return null;

  return (
    <div className="investment-reasoning">
      <section className="investment-reasoning__block">
        <h2 className="investment-reasoning__heading">Why these sectors</h2>
        {data.sectors.map((s) => (
          <div key={s.sector} className="investment-reasoning__item">
            <div className="investment-reasoning__item-head">
              <strong>{s.sector}</strong>
              {s.character && (
                <span className={`investment-reasoning__badge investment-reasoning__badge--${CHARACTER_TONE[s.character] || "gray"}`}>
                  {CHARACTER_LABEL[s.character] || s.character}
                </span>
              )}
            </div>
            <p className="investment-reasoning__item-body">{s.explanation}</p>
          </div>
        ))}
      </section>

      <section className="investment-reasoning__block">
        <h2 className="investment-reasoning__heading">Why these stocks</h2>
        {data.stocks.map((s) => (
          <div key={s.stock} className="investment-reasoning__item">
            <div className="investment-reasoning__item-head">
              <strong>{s.stock}</strong>
              {s.volatility_label && (
                <span className={`investment-reasoning__badge investment-reasoning__badge--${VOLATILITY_TONE[s.volatility_label] || "gray"}`}>
                  {s.volatility_label} volatility
                </span>
              )}
            </div>
            <p className="investment-reasoning__item-body">{s.explanation}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
