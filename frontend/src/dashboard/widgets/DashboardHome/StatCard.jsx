import React from "react";
import "./StatCard.css";

/**
 * @param {{ label: string, value: string, caption: string, tone?: "up" | "down" | "neutral" | "warn" }} props
 */
export default function StatCard({ label, value, caption, tone = "neutral" }) {
  return (
    <div className="stat-card">
      <p className="stat-card__label">{label}</p>
      <p className="stat-card__value">{value}</p>
      <p className={`stat-card__caption stat-card__caption--${tone}`}>{caption}</p>
    </div>
  );
}
