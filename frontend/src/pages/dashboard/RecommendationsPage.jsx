import React, { useEffect, useState } from "react";
import RecommendationsExplorer from "../widgets/Recommendations/RecommendationsExplorer";
import { recommendedStocks as defaultStocks } from "../../data/dashboardMock";
import "./PageShell.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

/**
 * /dashboard/recommendations — the full, filterable list of model-picked
 * stocks with SHAP/LIME reasoning per pick. Pulls GET /recommendations
 * from the backend; falls back to bundled mock data if that fails.
 */
export default function RecommendationsPage() {
  const [stocks, setStocks] = useState(defaultStocks);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const token = localStorage.getItem("access_token");

    async function load() {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE_URL}/recommendations`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Failed to load recommendations (${res.status})`);
        const data = await res.json();
        if (!cancelled) {
          setStocks(Array.isArray(data) ? data : data?.stocks || defaultStocks);
          setUsingFallback(false);
        }
      } catch (err) {
        if (!cancelled) {
          setStocks(defaultStocks);
          setUsingFallback(true);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="page-shell">
      <div className="page-shell__header">
        <div>
          <h1>Recommendations</h1>
          <p>Every stock the model currently suggests, with the reasoning behind each pick.</p>
        </div>
      </div>

      {usingFallback && !loading && (
        <p className="page-shell__notice">
          Showing sample data — couldn't reach the recommendations service.
        </p>
      )}

      <section className="page-shell__panel">
        {loading ? (
          <p className="page-shell__empty">Loading recommendations…</p>
        ) : (
          <RecommendationsExplorer stocks={stocks} />
        )}
      </section>
    </div>
  );
}
