import React, { useMemo, useState } from "react";
import { ArrowRight, ClipboardList, Sparkles } from "lucide-react";
import { historyEntries as defaultEntries } from "../../../data/dashboardMock";
import "./HistoryTable.css";

const BAND_COLORS = { Low: "teal", Medium: "amber", High: "danger" };

const TYPE_ICON = {
  "Risk Assessment": ClipboardList,
  "Recommendation Refresh": Sparkles,
};

const fmtRupee = (v) => `₹${Number(v || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

/**
 * @param {{ entries?: Array, isLoading?: boolean, onViewReport?: (reportId: string) => void }} props
 */
export default function HistoryTable({ entries, isLoading = false, onViewReport }) {
  const [bandFilter, setBandFilter] = useState("All");

  const safeEntries = Array.isArray(entries) ? entries : defaultEntries;
  const bands = useMemo(() => ["All", ...new Set(safeEntries.map((e) => e.band))], [safeEntries]);

  const filtered = useMemo(
    () => safeEntries.filter((e) => bandFilter === "All" || e.band === bandFilter),
    [safeEntries, bandFilter]
  );

  if (isLoading) {
    return (
      <ul className="history-list">
        {[0, 1, 2].map((i) => (
          <li key={i} className="history-list__item">
            <span className="dsb-skeleton" style={{ width: "36px", height: "36px", borderRadius: "10px" }} />
            <div style={{ flex: 1 }}>
              <span className="dsb-skeleton" style={{ width: "160px", height: "12px", marginBottom: "8px", display: "block" }} />
              <span className="dsb-skeleton" style={{ width: "220px", height: "10px", display: "block" }} />
            </div>
          </li>
        ))}
      </ul>
    );
  }

  if (filtered.length === 0) {
    return <div className="history-list-empty"><p>No history yet for this filter.</p></div>;
  }

  return (
    <div>
      <div className="history-list__filters">
        {bands.map((b) => (
          <button
            key={b}
            className={`history-list__filter-btn ${bandFilter === b ? "history-list__filter-btn--active" : ""}`}
            onClick={() => setBandFilter(b)}
          >
            {b}
          </button>
        ))}
      </div>

      <ol className="history-list">
        {filtered.map((entry, index) => {
          const Icon = TYPE_ICON[entry.type] || ClipboardList;
          return (
            <li key={entry.reportId || index} className="history-list__item" style={{ "--dsb-stagger": index }}>
              <span className="history-list__icon">
                <Icon size={16} strokeWidth={1.9} />
              </span>

              <div className="history-list__body">
                <div className="history-list__row-top">
                  <p className="history-list__type">{entry.type}</p>
                  <span className={`history-list__badge history-list__badge--${BAND_COLORS[entry.band] || "gray"}`}>
                    {entry.band} Risk
                  </span>
                </div>

                <p className="history-list__meta">
                  {entry.date} · Model {entry.modelVersion} · {entry.confidence}% confidence
                  {entry.portfolioValue ? ` · Portfolio ${fmtRupee(entry.portfolioValue)}` : ""}
                </p>
              </div>

              <button
                className="history-list__view-btn"
                onClick={() => onViewReport?.(entry.reportId)}
              >
                View report <ArrowRight size={14} strokeWidth={2} />
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
