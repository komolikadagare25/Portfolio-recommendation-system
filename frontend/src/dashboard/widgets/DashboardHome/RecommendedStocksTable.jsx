import React from "react";
import { recommendedStocks as defaultStocks } from "../../../data/dashboardMock";
import "./RecommendedStocksTable.css";

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

export default function RecommendedStocksTable({ stocks }) {
  // Use API data if available, otherwise use mock data
  const safeStocks = Array.isArray(stocks)
    ? stocks
    : Array.isArray(defaultStocks)
      ? defaultStocks
      : [];

  // Handle empty data
  if (safeStocks.length === 0) {
    return (
      <div className="stock-table-empty">
        <p>No recommended stocks available.</p>
      </div>
    );
  }

  // Find the highest stock weight
  const maxWeight = Math.max(
    ...safeStocks.map((stock) => Number(stock?.weight || 0))
  );

  return (
    <table className="stock-table">
      <thead>
        <tr>
          <th>Stock</th>
          <th>Sector</th>
          <th>Weight</th>
          <th>Exp. Return</th>
          <th>Risk</th>
        </tr>
      </thead>

      <tbody>
        {safeStocks.map((stock, index) => {
          const weight = Number(stock?.weight || 0);
          const expReturn = Number(stock?.expReturn || 0);

          const weightPercentage =
            maxWeight > 0 ? (weight / maxWeight) * 100 : 0;

          return (
            <tr
              key={stock?.symbol || `stock-${index}`}
            >
              {/* Stock */}
              <td>
                <p className="stock-table__symbol">
                  {stock?.symbol || "N/A"}
                </p>

                <p className="stock-table__name">
                  {stock?.name || "Unknown Stock"}
                </p>
              </td>

              {/* Sector */}
              <td>
                <span
                  className={`stock-table__badge stock-table__badge--${
                    SECTOR_COLORS[stock?.sector] || "gray"
                  }`}
                >
                  {stock?.sector || "Unknown"}
                </span>
              </td>

              {/* Weight */}
              <td>
                <div className="stock-table__weight">
                  <span className="stock-table__weight-track">
                    <span
                      className="stock-table__weight-fill"
                      style={{
                        width: `${weightPercentage}%`,
                      }}
                    />
                  </span>

                  <span className="stock-table__weight-value">
                    {weight}%
                  </span>
                </div>
              </td>

              {/* Expected Return */}
              <td className="stock-table__return">
                +{expReturn}%
              </td>

              {/* Risk */}
              <td>
                <span
                  className={`stock-table__badge stock-table__badge--${
                    RISK_COLORS[stock?.risk] || "gray"
                  }`}
                >
                  {stock?.risk || "Unknown"}
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}