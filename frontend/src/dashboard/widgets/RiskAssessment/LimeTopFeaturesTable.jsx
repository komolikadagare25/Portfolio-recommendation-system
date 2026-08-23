import React from "react";
import "./LimeTopFeaturesTable.css";

/**
 * @param {{ features: Array<{ feature: string, condition: string, weight: number }>, count?: number }} props
 */
export default function LimeTopFeaturesTable({ features, count = 5 }) {
  const positive = [...features]
    .filter((f) => f.weight >= 0)
    .sort((a, b) => b.weight - a.weight)
    .slice(0, count);

  const negative = [...features]
    .filter((f) => f.weight < 0)
    .sort((a, b) => a.weight - b.weight)
    .slice(0, count);

  return (
    <div className="lime-top-features">
      <div className="lime-top-features__col">
        <p className="lime-top-features__heading">
          <span className="lime-top-features__dot lime-top-features__dot--pos" />
          Supports the Prediction
        </p>
        <table className="lime-top-features__table">
          <thead>
            <tr>
              <th>condition</th>
              <th>weight</th>
            </tr>
          </thead>
          <tbody>
            {positive.map((f) => (
              <tr key={f.feature}>
                <td>{f.condition}</td>
                <td className="lime-top-features__value lime-top-features__value--pos">
                  {f.weight.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="lime-top-features__col">
        <p className="lime-top-features__heading">
          <span className="lime-top-features__dot lime-top-features__dot--neg" />
          Against the Prediction
        </p>
        <table className="lime-top-features__table">
          <thead>
            <tr>
              <th>condition</th>
              <th>weight</th>
            </tr>
          </thead>
          <tbody>
            {negative.map((f) => (
              <tr key={f.feature}>
                <td>{f.condition}</td>
                <td className="lime-top-features__value lime-top-features__value--neg">
                  {f.weight.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
