import React, { useState } from "react";
import { ChevronDown, Lightbulb } from "lucide-react";
import "./ShapPlainExplanation.css";

// Turns a raw feature name into a readable phrase, e.g. "fixed_deposits" -> "Fixed Deposits preference"
function humanize(feature) {
  const words = feature.replace(/_/g, " ");
  const titled = words.replace(/\b\w/g, (c) => c.toUpperCase());
  return titled;
}

/**
 * @param {{ predictedBand: string, topPositive: Array<{feature:string,value:number}>, topNegative: Array<{feature:string,value:number}> }} props
 */
export default function ShapPlainExplanation({ predictedBand, topPositive, topNegative }) {
  const [open, setOpen] = useState(true);

  return (
    <div className="shap-explanation">
      <button className="shap-explanation__toggle" onClick={() => setOpen((o) => !o)}>
        <Lightbulb size={16} strokeWidth={1.75} />
        SHAP Explanation in Simple Language
        <ChevronDown
          size={16}
          strokeWidth={2}
          className="shap-explanation__chevron"
          style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
        />
      </button>

      {open && (
        <div className="shap-explanation__body">
          <p>
            <strong>What is SHAP?</strong> SHAP shows how each answer in your
            questionnaire helped the AI reach its final decision — like a fair
            way of splitting the credit (or blame) for a prediction among all
            your answers.
          </p>

          <p>
            <strong>Why did the AI predict {predictedBand}?</strong>
          </p>

          <p>Because these factors pushed the prediction towards {predictedBand}:</p>
          <ul>
              {topPositive.slice(0, 3).map((f) => (
              <li key={f.feature}>
                Your <strong>{humanize(f.feature)}</strong>{f.answer_value !== null && f.answer_value !== undefined ? ` (you answered: ${f.answer_value})` : ""} strongly supported this outcome.
              </li>
            ))}
          </ul>

          <p>While these factors pulled against it (but were outweighed):</p>
          <ul>
              {topNegative.slice(0, 3).map((f) => (
              <li key={f.feature}>
                Your <strong>{humanize(f.feature)}</strong> answer slightly reduced the {predictedBand} score.
              </li>
            ))}
          </ul>

          <p>
            <strong>Overall:</strong> the positive influences outweighed the
            negative ones, so the AI settled on {predictedBand}.
          </p>
        </div>
      )}
    </div>
  );
}
