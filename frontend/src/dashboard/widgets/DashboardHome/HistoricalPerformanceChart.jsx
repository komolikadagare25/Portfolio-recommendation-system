import React, { useEffect, useState } from "react";

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
      <div style={{ display: "flex", gap: "6px", marginBottom: "12px" }}>
        {PERIODS.map((p) => (
          <button
            key={p.value}
            onClick={() => setPeriod(p.value)}
            style={{
              padding: "4px 12px",
              borderRadius: "6px",
              border: period === p.value ? "1px solid #3b82f6" : "1px solid #ddd",
              background: period === p.value ? "#eef4ff" : "#fff",
              color: period === p.value ? "#3b82f6" : "#333",
              fontWeight: period === p.value ? 600 : 400,
              cursor: "pointer",
            }}
          >
            {p.label}
          </button>
        ))}
      </div>

      {loading && <p>Loading historical performance...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {!loading && !error && data && data.portfolio_values.length >= 2 && (
        <ChartBody data={data} amount={amount} fmtRupee={fmtRupee} periodLabel={PERIODS.find((p) => p.value === period)?.label} />
      )}
      {!loading && !error && (!data || data.portfolio_values.length < 2) && (
        <p>Not enough data to show this chart for this timeframe.</p>
      )}

      <p style={{ fontSize: "0.85em", color: "#555", marginTop: "12px", background: "#f8f9fa", padding: "10px", borderRadius: "6px" }}>
        Short-term dips are normal for {riskLevel ? `a ${riskLevel}` : "a growth-oriented"} allocation
        — no single window (1 month or 10 years) tells the whole story. Your recommendation is built
        around your risk profile and time horizon, not a bet on any one period's return. Compare
        timeframes above rather than judging from just one.
      </p>
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
  const lineColor = isPositive ? "#22c55e" : "#ef4444";
  const gain = data.end_value - data.start_value;

  return (
    <div>
      <p style={{ marginBottom: "4px", color: "#666" }}>
        The {fmtRupee(data.included_amount)} of your ₹{amount.toLocaleString("en-IN")} that would
        have gone into Stocks, Mutual Funds, and Gold — if invested this way {periodLabel} ago:
      </p>

      <div style={{ marginBottom: "12px" }}>
        <span
          style={{
            display: "inline-block",
            padding: "2px 10px",
            borderRadius: "12px",
            background: isPositive ? "#dcfce7" : "#fee2e2",
            color: lineColor,
            fontWeight: 700,
            fontSize: "0.9em",
            marginRight: "10px",
          }}
        >
          {isPositive ? "▲ GAIN" : "▼ LOSS"}
        </span>
        <span style={{ fontSize: "1.4em", fontWeight: 700 }}>{fmtRupee(data.end_value)}</span>
        <span style={{ marginLeft: "10px", fontSize: "1.1em", fontWeight: 600, color: lineColor }}>
          {gain >= 0 ? "+" : ""}{fmtRupee(gain)} ({isPositive ? "+" : ""}{data.start_pct_change}%)
        </span>
        <span style={{ marginLeft: "8px", color: "#999" }}>from {fmtRupee(data.start_value)} invested</span>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "auto" }}>
        <text x={padding} y={padding - 10} fontSize="11" fill="#999">{fmtRupee(max)}</text>
        <text x={padding} y={height - padding + 15} fontSize="11" fill="#999">{fmtRupee(min)}</text>
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#eee" />
        <polyline points={points.join(" ")} fill="none" stroke={lineColor} strokeWidth="2.5" />
      </svg>

      {data.excluded_pct > 0 && (
        <p style={{ fontSize: "0.8em", color: "#999", marginTop: "8px" }}>
          Government Bonds &amp; Fixed Deposits ({data.excluded_pct}%) aren't market-linked and aren't shown here.
        </p>
      )}
      <p style={{ fontSize: "0.75em", color: "#999" }}>{data.note}</p>
    </div>
  );
}