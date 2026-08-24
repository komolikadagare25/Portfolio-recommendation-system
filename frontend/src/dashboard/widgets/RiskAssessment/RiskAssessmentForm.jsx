import React, { useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { riskQuestions } from "../../../data/riskQuestions";
import RiskResultTabs from "./RiskResultTabs";
import "./RiskAssessmentForm.css";

// Pre-fill default values for any slider-group question's fields, so those
// fields have a value even if the user never touches the sliders (matching
// the reference app, where sliders start at 4 and count as answered).
function buildInitialAnswers() {
  const initial = {};
  riskQuestions.forEach((q) => {
    if (q.type === "slider-group") {
      q.fields.forEach((f) => {
        initial[f.id] = f.default;
      });
    }
  });
  return initial;
}

/**
 * @param {{ onComplete: (answers: Record<string, string|number>) => void }} props
 * `answers` keys match your dataset's column names exactly (age, gender,
 * Investment_Avenues, Factor, Objective, Duration, Invest_Monitor, Expect,
 * Avenue, Stock_Marktet, Mutual_Funds, Equity_Market, Debentures,
 * Government_Bonds, Fixed_Deposits, PPF, Gold) — ready to send straight to
 * your backend/ML API.
 */
export default function RiskAssessmentForm({ onComplete }) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState(buildInitialAnswers);

  const totalQuestions = riskQuestions.length;
  const isResultStep = step === totalQuestions;
  const currentQuestion = riskQuestions[step];
  const progressPct = Math.min((step / totalQuestions) * 100, 100);

  const handleSelect = (value) => {
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: value }));
  };

  const handleNumberChange = (e) => {
    const val = e.target.value === "" ? "" : Number(e.target.value);
    setAnswers((prev) => ({ ...prev, [currentQuestion.id]: val }));
  };

  const handleSliderChange = (fieldId, value) => {
    setAnswers((prev) => ({ ...prev, [fieldId]: Number(value) }));
  };

  const handleNext = () => {
    if (step < totalQuestions - 1) setStep((s) => s + 1);
    else setStep(totalQuestions);
  };

  const handleBack = () => {
    if (step > 0) setStep((s) => s - 1);
  };

  const currentAnswer = currentQuestion ? answers[currentQuestion.id] : undefined;
  const isSliderGroup = currentQuestion?.type === "slider-group";
  const hasAnsweredCurrent =
    isSliderGroup || (currentAnswer !== undefined && currentAnswer !== "");

  if (isResultStep) {
    // TODO: once the backend exists, POST `answers` to your risk-assessment
    // endpoint here, receive back { band, confidence, shapFeatures }, and
    // pass THAT into RiskResultTabs instead of its built-in mock data.
    return <RiskResultTabs onContinue={() => onComplete?.(answers)} />;
  }

  return (
    <div className="risk-form">
      <div className="risk-form__progress-track">
        <div className="risk-form__progress-fill" style={{ width: `${progressPct}%` }} />
      </div>
      <p className="risk-form__step-label">
        Question {step + 1} of {totalQuestions}
      </p>

      <h2 className="risk-form__question">{currentQuestion.question}</h2>

      {currentQuestion.type === "number" && (
        <input
          type="number"
          className="risk-form__number-input"
          value={currentAnswer ?? ""}
          onChange={handleNumberChange}
          min={currentQuestion.min}
          max={currentQuestion.max}
          placeholder={`Enter a number (${currentQuestion.min}-${currentQuestion.max})`}
        />
      )}

      {currentQuestion.type === "select" && (
        <div className="risk-form__options">
          {currentQuestion.options.map((option) => (
            <button
              key={option}
              type="button"
              className={`risk-form__option ${currentAnswer === option ? "risk-form__option--selected" : ""}`}
              onClick={() => handleSelect(option)}
            >
              {option}
            </button>
          ))}
        </div>
      )}

      {isSliderGroup && (
        <div className="risk-form__slider-grid">
          {currentQuestion.fields.map((field) => (
            <div key={field.id} className="risk-form__slider-item">
              <div className="risk-form__slider-item-header">
                <span className="risk-form__slider-label">{field.label}</span>
                <span className="risk-form__slider-value">{answers[field.id]}</span>
              </div>
              <input
                type="range"
                className="risk-form__slider"
                min={field.min}
                max={field.max}
                value={answers[field.id]}
                onChange={(e) => handleSliderChange(field.id, e.target.value)}
              />
              <div className="risk-form__slider-scale">
                <span>{field.min}</span>
                <span>{field.max}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="risk-form__nav">
        <button type="button" className="risk-form__back-btn" onClick={handleBack} disabled={step === 0}>
          <ArrowLeft size={16} strokeWidth={2} /> Back
        </button>
        <button
          type="button"
          className="risk-form__next-btn"
          onClick={handleNext}
          disabled={!hasAnsweredCurrent}
        >
          {step === totalQuestions - 1 ? "Finish" : "Next"} <ArrowRight size={16} strokeWidth={2} />
        </button>
      </div>
    </div>
  );
}
