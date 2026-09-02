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

export default function RecommendedStocksTable({ stocks, isLoading = false }) {
  if (isLoading) {
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
          {[0, 1, 2, 3].map((i) => (
            <tr key={i}>
              <td><span className="dsb-skeleton" style={{ width: "90px", height: "12px", marginBottom: "6px" }} /><span className="dsb-skeleton" style={{ width: "60%", height: "10px" }} /></td>
              <td><span className="dsb-skeleton" style={{ width: "70px", height: "20px", borderRadius: "6px" }} /></td>
              <td><span className="dsb-skeleton" style={{ width: "100%", height: "10px" }} /></td>
              <td><span className="dsb-skeleton" style={{ width: "40px", height: "12px" }} /></td>
              <td><span className="dsb-skeleton" style={{ width: "60px", height: "20px", borderRadius: "6px" }} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

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
              className="stock-table__row"
              style={{ "--dsb-stagger": index }}
            >
              {/* Stock */}
              <td data-label="Stock">
                <p className="stock-table__symbol">
                  {stock?.symbol || "N/A"}
                </p>

                <p className="stock-table__name">
                  {stock?.name || "Unknown Stock"}
                </p>
              </td>

              {/* Sector */}
              <td data-label="Sector">
                <span
                  className={`stock-table__badge stock-table__badge--${
                    SECTOR_COLORS[stock?.sector] || "gray"
                  }`}
                >
                  {stock?.sector || "Unknown"}
                </span>
              </td>

              {/* Weight */}
              <td data-label="Weight">
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

              {/* Expected Return — positive expected return reads green,
                  consistent with amounts elsewhere on the dashboard */}
              <td className="stock-table__return dsb-amount--positive" data-label="Exp. Return">
                +{expReturn}%
              </td>

              {/* Risk */}
              <td data-label="Risk">
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