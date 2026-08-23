import React from "react";

/**
 * Tiny inline line chart used inside the market ticker card.
 * @param {{ points: string, up: boolean }} props
 */
export default function Sparkline({ points, up }) {
  return (
    <svg width="120" height="32" viewBox="0 0 120 32" className="sparkline">
      <polyline
        points={points}
        fill="none"
        className={up ? "sparkline__line sparkline__line--up" : "sparkline__line sparkline__line--down"}
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
