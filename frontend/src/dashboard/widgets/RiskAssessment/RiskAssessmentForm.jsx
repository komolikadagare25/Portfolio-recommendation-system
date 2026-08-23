import React, { useState } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2 } from "lucide-react";
import { riskQuestions } from "../../../data/riskQuestions";
import "./RiskAssessmentForm.css";

/**
 * @param {{ onComplete: (answers: Record<string, string|number>) => void }} props
 * `answers` keys match your dataset's column names exactly (age, gender,
 * Investment_Avenues, Factor, Objective, Duration, Invest_Monitor, Expect,
 * Avenue, Stock_Marktet) — ready to send straight to your backend/ML API.
 */
export default function RiskAssessmentForm({ onComplete }) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});

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

  const handleNext = () => {
    if (step < totalQuestions - 1) setStep((s) => s + 1);
    else setStep(totalQuestions);
  };

  const handleBack = () => {
    if (step > 0) setStep((s) => s - 1);
  };

  const currentAnswer = currentQuestion ? answers[currentQuestion.id] : undefined;
  const hasAnsweredCurrent = currentAnswer !== undefined && currentAnswer !== "";

  if (isResultStep) {
    return (
      <div className="risk-form risk-form--result">
        <CheckCircle2 size={40} strokeWidth={1.5} className="risk-form__result-icon" />
        <p className="risk-form__result-label">ALL SET</p>
        <p className="risk-form__result-band">Answers ready</p>
        <p className="risk-form__result-desc">
          Your {totalQuestions} answers are ready to be sent to the risk model.
          {/* TODO: once the backend endpoint exists, POST `answers` here instead of navigating directly */}
        </p>
        <button className="risk-form__submit-btn" onClick={() => onComplete?.(answers)}>
          Continue to dashboard <ArrowRight size={16} strokeWidth={2} />
        </button>
      </div>
    );
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

      {currentQuestion.type === "number" ? (
        <input
          type="number"
          className="risk-form__number-input"
          value={currentAnswer ?? ""}
          onChange={handleNumberChange}
          min={currentQuestion.min}
          max={currentQuestion.max}
          placeholder={`Enter a number (${currentQuestion.min}-${currentQuestion.max})`}
        />
      ) : (
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
