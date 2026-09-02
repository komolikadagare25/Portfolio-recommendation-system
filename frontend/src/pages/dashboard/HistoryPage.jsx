import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import HistoryTable from "../widgets/History/HistoryTable";
import { historyEntries as defaultEntries } from "../../data/dashboardMock";
import "./PageShell.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

/**
 * /dashboard/history — every past risk assessment and recommendation
 * refresh, newest first. Pulls GET /reports from the backend; falls back
 * to bundled mock data if that call fails.
 */
export default function HistoryPage() {
  const [entries, setEntries] = useState(defaultEntries);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    const token = localStorage.getItem("access_token");

    async function load() {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE_URL}/reports`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Failed to load history (${res.status})`);
        const data = await res.json();
        if (!cancelled) {
          setEntries(Array.isArray(data) ? data : data?.reports || defaultEntries);
          setUsingFallback(false);
        }
      } catch (err) {
        if (!cancelled) {
          setEntries(defaultEntries);
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
          <h1>History</h1>
          <p>Every past risk assessment and recommendation refresh, newest first.</p>
        </div>
      </div>

      {usingFallback && !loading && (
        <p className="page-shell__notice">
          Showing sample data — couldn't reach the history service.
        </p>
      )}

      <section className="page-shell__panel">
        <HistoryTable
          entries={entries}
          isLoading={loading}
          onViewReport={(reportId) => navigate(`/dashboard/risk-assessment?report=${reportId}`)}
        />
      </section>
    </div>
  );
}
