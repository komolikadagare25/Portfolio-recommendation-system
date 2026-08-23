import React from "react";
import { allocation as defaultAllocation } from "../../../data/dashboardMock";
import "./AllocationDonut.css";

export default function AllocationDonut({
  data = defaultAllocation,
  centerLabel = "Portfolio\nAllocation",
}) {
  // Make sure data is always an array
  const safeData = Array.isArray(data) ? data : defaultAllocation;

  // Calculate total allocation
  const total = safeData.reduce(
    (sum, item) => sum + Number(item?.value || 0),
    0
  );

  const radius = 52;
  const circumference = 2 * Math.PI * radius;

  let offsetAcc = 0;

  // Create donut segments
  const segments =
    total > 0
      ? safeData.map((item, index) => {
          const value = Number(item?.value || 0);
          const fraction = value / total;
          const dash = fraction * circumference;

          const segment = {
            ...item,
            value,
            dash,
            gap: circumference - dash,
            offset: -offsetAcc * circumference,
            key: item?.label || `segment-${index}`,
          };

          offsetAcc += fraction;

          return segment;
        })
      : [];

  return (
    <div className="allocation-donut">
      <div className="allocation-donut__chart-wrap">
        <svg
          viewBox="0 0 140 140"
          className="allocation-donut__svg"
        >
          {/* Background ring */}
          <circle
            cx="70"
            cy="70"
            r={radius}
            fill="none"
            stroke="var(--line)"
            strokeWidth="18"
          />

          {/* Donut segments */}
          {segments.map((segment) => (
            <circle
              key={segment.key}
              cx="70"
              cy="70"
              r={radius}
              fill="none"
              stroke={segment.color || "var(--accent)"}
              strokeWidth="18"
              strokeDasharray={`${segment.dash} ${segment.gap}`}
              strokeDashoffset={segment.offset}
              transform="rotate(-90 70 70)"
              strokeLinecap="butt"
            />
          ))}
        </svg>

        {/* Center text */}
        {centerLabel && (
          <div className="allocation-donut__center">
            <span>
              {centerLabel.split("\n").map((line, index, lines) => (
                <React.Fragment key={index}>
                  {line}
                  {index < lines.length - 1 && <br />}
                </React.Fragment>
              ))}
            </span>
          </div>
        )}
      </div>

      {/* Legend */}
      <ul className="allocation-donut__legend">
        {safeData.map((item, index) => (
          <li
            key={item?.label || `legend-${index}`}
            className="allocation-donut__legend-row"
          >
            <span className="allocation-donut__legend-left">
              <span
                className="allocation-donut__dot"
                style={{
                  background: item?.color || "var(--accent)",
                }}
              />

              {item?.label || "Unknown"}
            </span>

            <span className="allocation-donut__legend-value">
              {Number(item?.value || 0)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}