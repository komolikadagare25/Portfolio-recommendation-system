import React, { useEffect, useState } from "react";
import "./HistoricalPerformanceChart.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const PERIODS = [
  { value: "6mo", label: "6M" },
  { value: "1y", label: "1Y" },
  { value: "3y", label: "3Y" },
  { value: "5y", label: "5Y" },
];

export default function HistoricalPerformanceChart({ reportId, amount = 10000, riskLevel }) {
  const [period, setPeriod] = useState("1y");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const token = localStorage.getItem("access_token");

  const load = async (amt, per) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE_URL}/reports/${reportId}/historical-performance?period=${per}&amount=${amt}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error(`Failed to load (${res.status})`);
      setData(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (reportId) load(amount, period);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId, amount, period]);

  const fmtRupee = (v) => `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

  return (
    <div>
      <div className="perf-chart__periods">
        {PERIODS.map((p) => (
          <button
            key={p.value}
            onClick={() => setPeriod(p.value)}
            className={`perf-chart__period-btn ${period === p.value ? "perf-chart__period-btn--active" : ""}`}
            aria-pressed={period === p.value}
          >
            {p.label}
          </button>
        ))}
      </div>

      {loading && <ChartSkeleton />}

      {!loading && error && (
        <p className="perf-chart__error" role="alert">{error}</p>
      )}

      {!loading && !error && data && data.portfolio_values.length >= 2 && (
        <ChartBody data={data} amount={amount} fmtRupee={fmtRupee} periodLabel={PERIODS.find((p) => p.value === period)?.label} />
      )}
      {!loading && !error && (!data || data.portfolio_values.length < 2) && (
        <p className="perf-chart__empty">Not enough data to show this chart for this timeframe.</p>
      )}

      <p className="perf-chart__note">
        Short-term dips are normal for {riskLevel ? `a ${riskLevel}` : "a growth-oriented"} allocation
        — no single window (1 month or 10 years) tells the whole story. Your recommendation is built
        around your risk profile and time horizon, not a bet on any one period's return. Compare
        timeframes above rather than judging from just one.
      </p>
    </div>
  );
}

// A shimmering placeholder that mimics the shape of the real chart, so the
// user can see something is actively happening rather than a blank gap.
function ChartSkeleton() {
  return (
    <div className="perf-chart__skeleton" aria-busy="true">
      <div className="dsb-loading-row">
        <span className="dsb-spinner" />
        Fetching historical performance
        <span className="dsb-loading-dots"><span /><span /><span /></span>
      </div>
      <div className="perf-chart__skeleton-bars">
        {[38, 55, 42, 66, 50, 72, 60, 80, 68, 90, 76, 95].map((h, i) => (
          <span key={i} className="dsb-skeleton" style={{ height: `${h}%` }} />
        ))}
      </div>
    </div>
  );
}

function ChartBody({ data, amount, fmtRupee, periodLabel }) {
  const values = data.portfolio_values;
  const width = 600;
  const height = 220;
  const padding = 40;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = values.map((v, i) => {
    const x = padding + (i / (values.length - 1)) * (width - padding * 2);
    const y = height - padding - ((v - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });

  const isPositive = data.start_pct_change >= 0;
  const gain = data.end_value - data.start_value;

  // Rough path length estimate for the draw-in animation (doesn't need to
  // be exact — just longer than the actual line so it fully reveals).
  const approxLineLength = points.length * (width / points.length) * 1.4;

  return (
    <div>
      <p className="perf-chart__summary-line">
        The {fmtRupee(data.included_amount)} of your ₹{amount.toLocaleString("en-IN")} that would
        have gone into Stocks, Mutual Funds, and Gold — if invested this way {periodLabel} ago:
      </p>

      <div className="perf-chart__headline">
        <span className={`perf-chart__badge ${isPositive ? "perf-chart__badge--gain" : "perf-chart__badge--loss"}`}>
          {isPositive ? "▲ GAIN" : "▼ LOSS"}
        </span>
        <span className="perf-chart__end-value">{fmtRupee(data.end_value)}</span>
        <span className={`perf-chart__gain ${isPositive ? "perf-chart__gain--positive" : "perf-chart__gain--negative"}`}>
          {gain >= 0 ? "+" : ""}{fmtRupee(gain)} ({isPositive ? "+" : ""}{data.start_pct_change}%)
        </span>
        <span className="perf-chart__from">from {fmtRupee(data.start_value)} invested</span>
      </div>

      <div className="perf-chart__svg-wrap">
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "auto" }}>
          <text x={padding} y={padding - 10} fontSize="11" fill="var(--muted-dim)">{fmtRupee(max)}</text>
          <text x={padding} y={height - padding + 15} fontSize="11" fill="var(--muted-dim)">{fmtRupee(min)}</text>
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--line)" />
          <polyline
            points={points.join(" ")}
            className="perf-chart__line"
            stroke={isPositive ? "var(--success)" : "var(--danger)"}
            style={{
              strokeDasharray: approxLineLength,
              "--dsb-line-length": approxLineLength,
            }}
          />
        </svg>
      </div>

      {data.excluded_pct > 0 && (
        <p className="perf-chart__excluded-note">
          Government Bonds &amp; Fixed Deposits ({data.excluded_pct}%) aren't market-linked and aren't shown here.
        </p>
      )}
      <p className="perf-chart__footnote">{data.note}</p>
    </div>
  );
}
