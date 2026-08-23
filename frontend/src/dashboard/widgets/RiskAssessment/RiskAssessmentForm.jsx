import React, { useState } from "react";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { riskQuestions } from "../../../data/riskQuestions";
import RiskResultTabs from "./RiskResultTabs";
import { fetchRiskAssessment } from "../../../api/riskAssessment";
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
  const [result, setResult] = useState(null); // { prediction, portfolio, shap, lime }
  const [status, setStatus] = useState("idle"); // idle | loading | error
  const [errorMessage, setErrorMessage] = useState("");

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

  const runPrediction = async (finalAnswers) => {
    setStatus("loading");
    setErrorMessage("");
    try {
      const data = await fetchRiskAssessment(finalAnswers);
      setResult(data);
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setErrorMessage(err.message || "Something went wrong reaching the prediction API.");
    }
  };

  const handleNext = () => {
    if (step < totalQuestions - 1) {
      setStep((s) => s + 1);
    } else {
      setStep(totalQuestions);
      runPrediction(answers);
    }
  };

  const handleBack = () => {
    if (step > 0) setStep((s) => s - 1);
  };

  const currentAnswer = currentQuestion ? answers[currentQuestion.id] : undefined;
  const hasAnsweredCurrent = currentAnswer !== undefined && currentAnswer !== "";

  if (isResultStep) {
    if (status === "loading") {
      return (
        <div className="risk-form__status">
          <Loader2 size={22} strokeWidth={2} className="risk-form__spinner" />
          Running your prediction (model + SHAP + LIME)…
        </div>
      );
    }

    if (status === "error") {
      return (
        <div className="risk-form__status risk-form__status--error">
          <p>{errorMessage}</p>
          <button type="button" className="risk-form__next-btn" onClick={() => runPrediction(answers)}>
            Try again
          </button>
        </div>
      );
    }

    // `result` is null until the API responds; RiskResultTabs falls back to
    // its bundled mock data if you pass it nothing, so this never crashes
    // even before your backend is wired up.
    return (
      <RiskResultTabs
        prediction={result?.prediction}
        portfolio={result?.portfolio}
        shap={result?.shap}
        lime={result?.lime}
        onContinue={() => onComplete?.(answers)}
      />
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
