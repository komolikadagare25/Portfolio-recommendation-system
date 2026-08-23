import React, { useState } from "react";
import { ChevronDown, Lightbulb } from "lucide-react";
import "./LimePlainExplanation.css";

// Turns a raw condition string into a slightly friendlier phrase for prose,
// e.g. "equity_market <= 2.00" -> "equity market <= 2.00"
function humanizeCondition(condition) {
  return condition.replace(/_/g, " ");
}

/**
 * @param {{ predictedBand: string, topPositive: Array<{feature:string,condition:string,weight:number}>, topNegative: Array<{feature:string,condition:string,weight:number}> }} props
 */
export default function LimePlainExplanation({ predictedBand, topPositive, topNegative }) {
  const [open, setOpen] = useState(true);

  return (
    <div className="lime-explanation">
      <button className="lime-explanation__toggle" onClick={() => setOpen((o) => !o)}>
        <Lightbulb size={16} strokeWidth={1.75} />
        LIME Explanation in Simple Language
        <ChevronDown
          size={16}
          strokeWidth={2}
          className="lime-explanation__chevron"
          style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
        />
      </button>

      {open && (
        <div className="lime-explanation__body">
          <p>
            <strong>What is LIME?</strong> LIME (Local Interpretable
            Model-agnostic Explanations) builds a small, simple model that
            mimics the AI's behavior <em>just around your specific answers</em>
            — then reads the effect of each answer off that simple model.
            It's a different lens on the same prediction: SHAP measures each
            answer's fair share of credit overall, LIME asks "if your answer
            had been slightly different, how much would the prediction have
            moved, right here?"
          </p>

          <p>
            <strong>Why did the AI predict {predictedBand}?</strong>
          </p>

          <p>Locally, these specific answers pushed the prediction towards {predictedBand}:</p>
          <ul>
            {topPositive.slice(0, 3).map((f) => (
              <li key={f.feature}>
                <strong>{humanizeCondition(f.condition)}</strong> supported this outcome.
              </li>
            ))}
          </ul>

          <p>While these pulled against it (but were outweighed):</p>
          <ul>
            {topNegative.slice(0, 3).map((f) => (
              <li key={f.feature}>
                <strong>{humanizeCondition(f.condition)}</strong> slightly reduced the {predictedBand} score.
              </li>
            ))}
          </ul>

          <p>
            <strong>Overall:</strong> around your specific set of answers, the
            local model agrees with SHAP that the positive influences
            outweighed the negative ones, landing on {predictedBand}.
          </p>
        </div>
      )}
    </div>
  );
}
