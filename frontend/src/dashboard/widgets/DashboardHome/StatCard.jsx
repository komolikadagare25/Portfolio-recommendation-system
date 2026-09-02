import React from "react";
import "./StatCard.css";

const VALUE_COLOR = {
  up: "var(--success-strong)",
  down: "var(--danger)",
  warn: "var(--warning)",
  neutral: "var(--text)",
  info: "var(--indigo)",
};

const CAPTION_COLOR = {
  up: "var(--success)",
  down: "var(--danger)",
  warn: "var(--warning)",
  neutral: "var(--muted)",
  info: "var(--indigo)",
};

/**
 * @param {{ label: string, value: string, caption: string, tone?: "up" | "down" | "neutral" | "warn" | "info", isLoading?: boolean, index?: number }} props
 */
export default function StatCard({ label, value, caption, tone = "neutral", isLoading = false, index = 0 }) {
  if (isLoading) {
    return (
      <div className="stat-card" style={{ "--dsb-stagger": index }}>
        <span className="dsb-skeleton" style={{ width: "70px", height: "10px", marginBottom: "12px" }} />
        <span className="dsb-skeleton" style={{ width: "90px", height: "22px", marginBottom: "10px" }} />
        <span className="dsb-skeleton" style={{ width: "60%", height: "10px" }} />
      </div>
    );
  }

  // Color is set inline (not just via className) so it can't be silently
  // overridden by another stylesheet with equal-or-higher specificity
  // loading later in the cascade — this is the source of truth.
  return (
    <div className="stat-card" style={{ "--dsb-stagger": index }}>
      <p className="stat-card__label">{label}</p>
      <p className={`stat-card__value stat-card__value--${tone}`} style={{ color: VALUE_COLOR[tone] || VALUE_COLOR.neutral }}>
        {value}
      </p>
      <p className={`stat-card__caption stat-card__caption--${tone}`} style={{ color: CAPTION_COLOR[tone] || CAPTION_COLOR.neutral }}>
        {caption}
      </p>
    </div>
  );
}
