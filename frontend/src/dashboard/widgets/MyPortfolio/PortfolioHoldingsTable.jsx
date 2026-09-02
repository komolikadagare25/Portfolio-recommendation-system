import React, { useMemo, useState } from "react";
import { ArrowUpDown } from "lucide-react";
import { portfolioHoldings as defaultHoldings } from "../../../data/dashboardMock";
import "./PortfolioHoldingsTable.css";

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

const fmtRupee = (v) => `₹${Number(v || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

const SORT_FIELDS = [
  { key: "value", label: "Current Value" },
  { key: "pnlPct", label: "P&L %" },
  { key: "symbol", label: "Name" },
];

/**
 * @param {{ holdings?: Array<{symbol,name,sector,qty,avgCost,ltp,risk}>, isLoading?: boolean }} props
 */
export default function PortfolioHoldingsTable({ holdings, isLoading = false }) {
  const [sortKey, setSortKey] = useState("value");

  const safeHoldings = Array.isArray(holdings) ? holdings : defaultHoldings;

  const rows = useMemo(() => {
    return safeHoldings.map((h) => {
      const qty = Number(h?.qty || 0);
      const avgCost = Number(h?.avgCost || 0);
      const ltp = Number(h?.ltp || 0);
      const invested = qty * avgCost;
      const value = qty * ltp;
      const pnl = value - invested;
      const pnlPct = invested > 0 ? (pnl / invested) * 100 : 0;
      return { ...h, qty, avgCost, ltp, invested, value, pnl, pnlPct };
    });
  }, [safeHoldings]);

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      if (sortKey === "symbol") return (a.symbol || "").localeCompare(b.symbol || "");
      return b[sortKey] - a[sortKey];
    });
    return copy;
  }, [rows, sortKey]);

  if (isLoading) {
    return (
      <table className="holdings-table">
        <thead>
          <tr>
            <th>Stock</th><th>Qty</th><th>Avg Cost</th><th>LTP</th><th>Value</th><th>P&amp;L</th>
          </tr>
        </thead>
        <tbody>
          {[0, 1, 2, 3].map((i) => (
            <tr key={i}>
              <td><span className="dsb-skeleton" style={{ width: "90px", height: "12px" }} /></td>
              <td><span className="dsb-skeleton" style={{ width: "30px", height: "12px" }} /></td>
              <td><span className="dsb-skeleton" style={{ width: "50px", height: "12px" }} /></td>
              <td><span className="dsb-skeleton" style={{ width: "50px", height: "12px" }} /></td>
              <td><span className="dsb-skeleton" style={{ width: "70px", height: "12px" }} /></td>
              <td><span className="dsb-skeleton" style={{ width: "70px", height: "12px" }} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  if (sorted.length === 0) {
    return (
      <div className="holdings-table-empty">
        <p>No holdings yet — recommendations you act on will show up here.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="holdings-table__toolbar">
        <span className="holdings-table__toolbar-label">Sort by</span>
        <div className="holdings-table__sort-group">
          {SORT_FIELDS.map((f) => (
            <button
              key={f.key}
              className={`holdings-table__sort-btn ${sortKey === f.key ? "holdings-table__sort-btn--active" : ""}`}
              onClick={() => setSortKey(f.key)}
            >
              <ArrowUpDown size={12} strokeWidth={2} />
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <table className="holdings-table">
        <thead>
          <tr>
            <th>Stock</th>
            <th>Sector</th>
            <th>Qty</th>
            <th>Avg Cost</th>
            <th>LTP</th>
            <th>Current Value</th>
            <th>P&amp;L</th>
            <th>Risk</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((h, index) => {
            const gaining = h.pnl >= 0;
            return (
              <tr key={h.symbol || `holding-${index}`} className="holdings-table__row" style={{ "--dsb-stagger": index }}>
                <td data-label="Stock">
                  <p className="holdings-table__symbol">{h.symbol || "N/A"}</p>
                  <p className="holdings-table__name">{h.name || "Unknown Stock"}</p>
                </td>
                <td data-label="Sector">
                  <span className={`holdings-table__badge holdings-table__badge--${SECTOR_COLORS[h.sector] || "gray"}`}>
                    {h.sector || "Unknown"}
                  </span>
                </td>
                <td data-label="Qty" className="holdings-table__num">{h.qty}</td>
                <td data-label="Avg Cost" className="holdings-table__num">{fmtRupee(h.avgCost)}</td>
                <td data-label="LTP" className="holdings-table__num">{fmtRupee(h.ltp)}</td>
                <td data-label="Current Value" className="holdings-table__num holdings-table__value">{fmtRupee(h.value)}</td>
                <td data-label="P&L" className={`holdings-table__num ${gaining ? "dsb-amount--positive" : "dsb-amount--negative"}`}>
                  {gaining ? "+" : ""}{fmtRupee(h.pnl)}
                  <span className="holdings-table__pnl-pct">({gaining ? "+" : ""}{h.pnlPct.toFixed(1)}%)</span>
                </td>
                <td data-label="Risk">
                  <span className={`holdings-table__badge holdings-table__badge--${RISK_COLORS[h.risk] || "gray"}`}>
                    {h.risk || "Unknown"}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
