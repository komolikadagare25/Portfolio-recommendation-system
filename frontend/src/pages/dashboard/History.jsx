import React, { useEffect, useState } from "react";
import { ClipboardList } from "lucide-react";
import "./History.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const RISK_TONE = { Low: "teal", Medium: "amber", High: "danger" };

export default function History() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);
  const [selectedLoading, setSelectedLoading] = useState(false);

  const token = localStorage.getItem("access_token");

  useEffect(() => {
    async function loadReports() {
      try {
        const res = await fetch(`${API_BASE_URL}/reports`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`Failed to load reports (${res.status})`);
        const data = await res.json();
        setReports(data);
        if (data.length > 0) openReport(data[0].id);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const openReport = async (reportId) => {
    setSelectedLoading(true);
    setSelectedReport(null);
    try {
      const res = await fetch(`${API_BASE_URL}/reports/${reportId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed to load report (${res.status})`);
      const data = await res.json();
      setSelectedReport(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setSelectedLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="history-page">
        <h1>History</h1>
        <div className="history-page__panel">
          <span className="dsb-skeleton" style={{ width: "180px", height: "16px", marginBottom: "12px" }} />
          <span className="dsb-skeleton" style={{ width: "90%", height: "12px" }} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="history-page">
        <h1>History</h1>
        <p className="history-page__error">{error}</p>
      </div>
    );
  }

  return (
    <div className="history-page">
      <h1>History</h1>

      {reports.length === 0 && (
        <div className="history-page__empty">
          <div className="history-page__empty-icon">
            <ClipboardList size={26} strokeWidth={1.75} />
          </div>
          <h2>No history yet</h2>
          <p>Complete a Risk Assessment to generate your first report.</p>
        </div>
      )}

      {reports.length > 0 && (
        <div className="history-page__layout">
          <ul className="history-page__list">
            {reports.map((r) => {
              const isActive = selectedReport?.id === r.id;
              return (
                <li key={r.id}>
                  <button
                    onClick={() => openReport(r.id)}
                    className={`history-page__list-item ${isActive ? "history-page__list-item--active" : ""}`}
                  >
                    <div className="history-page__list-item-top">
                      <span className="history-page__list-item-band">{r.risk_level}</span>
                      <span className={`history-page__badge history-page__badge--${RISK_TONE[r.risk_level] || "gray"}`}>
                        {(parseFloat(r.confidence) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="history-page__list-item-date">
                      {new Date(r.created_at).toLocaleString()}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>

          <div className="history-page__panel">
            {selectedLoading && (
              <>
                <span className="dsb-skeleton" style={{ width: "160px", height: "16px", marginBottom: "12px" }} />
                <span className="dsb-skeleton" style={{ width: "90%", height: "12px" }} />
              </>
            )}

            {!selectedLoading && selectedReport && (
              <>
                <div className="history-page__detail-head">
                  <h2>{selectedReport.risk_level} Risk</h2>
                  <span className={`history-page__badge history-page__badge--${RISK_TONE[selectedReport.risk_level] || "gray"}`}>
                    {(parseFloat(selectedReport.confidence) * 100).toFixed(1)}% confidence
                  </span>
                </div>

                {selectedReport.portfolio_result.risk_description && (
                  <p className="history-page__description">{selectedReport.portfolio_result.risk_description}</p>
                )}

                <h3 className="history-page__section-title">Asset Allocation</h3>
                <ul className="history-page__allocation-list">
                  {Object.entries(selectedReport.portfolio_result.asset_allocation).map(([k, v]) => (
                    <li key={k} className="history-page__allocation-row">
                      <span>{k}</span>
                      <div className="history-page__allocation-track">
                        <span className="history-page__allocation-fill" style={{ width: `${v}%` }} />
                      </div>
                      <span className="history-page__allocation-value">{v}%</span>
                    </li>
                  ))}
                </ul>

                <h3 className="history-page__section-title">Recommended Sectors</h3>
                <ul className="history-page__chip-list">
                  {selectedReport.portfolio_result.recommended_sectors.map((s) => (
                    <li key={s} className="history-page__chip">{s}</li>
                  ))}
                </ul>

                <h3 className="history-page__section-title">Recommended Stocks</h3>
                <ul className="history-page__chip-list">
                  {selectedReport.portfolio_result.recommended_stocks.map((s) => (
                    <li key={s} className="history-page__chip history-page__chip--alt">{s}</li>
                  ))}
                </ul>

                <p className="history-page__advice">{selectedReport.portfolio_result.investment_advice}</p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
