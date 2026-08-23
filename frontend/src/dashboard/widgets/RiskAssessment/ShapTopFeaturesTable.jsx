import React from "react";
import "./ShapTopFeaturesTable.css";

/**
 * @param {{ features: Array<{ feature: string, value: number }>, count?: number }} props
 */
export default function ShapTopFeaturesTable({ features, count = 5 }) {
  const positive = [...features]
    .filter((f) => f.value >= 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, count);

  const negative = [...features]
    .filter((f) => f.value < 0)
    .sort((a, b) => a.value - b.value)
    .slice(0, count);

  return (
    <div className="shap-top-features">
      <div className="shap-top-features__col">
        <p className="shap-top-features__heading">
          <span className="shap-top-features__dot shap-top-features__dot--pos" />
          Top Positive Features
        </p>
        <table className="shap-top-features__table">
          <thead>
            <tr>
              <th>feature</th>
              <th>impact</th>
            </tr>
          </thead>
          <tbody>
            {positive.map((f) => (
              <tr key={f.feature}>
                <td>{f.feature}</td>
                <td className="shap-top-features__value shap-top-features__value--pos">
                  {f.value.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="shap-top-features__col">
        <p className="shap-top-features__heading">
          <span className="shap-top-features__dot shap-top-features__dot--neg" />
          Top Negative Features
        </p>
        <table className="shap-top-features__table">
          <thead>
            <tr>
              <th>feature</th>
              <th>impact</th>
            </tr>
          </thead>
          <tbody>
            {negative.map((f) => (
              <tr key={f.feature}>
                <td>{f.feature}</td>
                <td className="shap-top-features__value shap-top-features__value--neg">
                  {f.value.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
