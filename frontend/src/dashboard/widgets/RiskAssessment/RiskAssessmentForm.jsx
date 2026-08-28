import React, { useState, useEffect } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { riskQuestions } from "../../../data/riskQuestions";
import RiskResultTabs from "./RiskResultTabs";
import "./RiskAssessmentForm.css";
import { usePortfolio } from "../../../context/PortfolioContext";

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

function reportToResultProps(report, answers) {
  const confidencePct = +(parseFloat(report.confidence) * 100).toFixed(2);

  return {
    prediction: {
      riskLevel: report.risk_level,
      confidence: confidencePct,
      investmentHorizon: report.portfolio_result.investment_horizon,
      riskDescription: report.portfolio_result.risk_description,
      investorSummary: {
        age: answers.age,
        objective: answers.Objective,
        preferredAsset: answers.Avenue,
        duration: answers.Duration,
      },
    },
    portfolio: {
      allocation: Object.entries(report.portfolio_result.asset_allocation).map(([label, pct]) => ({
        label,
        pct,
      })),
      sectors: report.portfolio_result.recommended_sectors,
      stocks: report.portfolio_result.recommended_stocks,
      advice: report.portfolio_result.investment_advice,
    },
    shap: {
      predictedBand: report.risk_level,
      confidence: confidencePct,
      features: [
        ...report.shap_result.top_positive_features,
        ...report.shap_result.top_negative_features,
      ].map((f) => ({ feature: f.feature, value: f.impact })),
    },
    lime: {
      predictedBand: report.risk_level,
      confidence: confidencePct,
      // intercept / localModelScore intentionally omitted — the ML
      // pipeline doesn't compute them; LimeExplanationPanel handles
      // their absence gracefully.
      features: report.lime_result.top_features.map((f) => ({
        feature: f.feature,
        condition: f.feature,
        weight: f.weight,
      })),
    },
  };
}

/**
 * @param {{
 *   onSubmitAnswers: (answers: object) => Promise<object>,
 *   onComplete: (answers: object) => void
 * }} props
 */
export default function RiskAssessmentForm({ onSubmitAnswers, onComplete }) {
  const [step, setStep] = useState(0);
  const { setResult } = usePortfolio();
  const [answers, setAnswers] = useState(buildInitialAnswers);
  const [report, setReport] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const totalQuestions = riskQuestions.length;
  const isResultStep = step === totalQuestions;
  const currentQuestion = riskQuestions[step];
  const progressPct = Math.min((step / totalQuestions) * 100, 100);

  useEffect(() => {
    if (!isResultStep || report || submitting) return;

    setSubmitting(true);
    setSubmitError(null);
    onSubmitAnswers(answers)
      .then((data) => {
        setReport(data);
        setResult(reportToResultProps(data, answers));
      })
      .catch((err) => setSubmitError(err.message))
      .finally(() => setSubmitting(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isResultStep]);

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
    if (submitting) {
      return <div className="risk-form"><p>Generating your report...</p></div>;
    }
    if (submitError) {
      return (
        <div className="risk-form">
          <p style={{ color: "red" }}>{submitError}</p>
          <button
            type="button"
            className="risk-form__next-btn"
            onClick={() => {
              setReport(null);
              setSubmitError(null);
            }}
          >
            Retry
          </button>
        </div>
      );
    }
    if (report) {
      const resultProps = reportToResultProps(report, answers);
      return (
        <RiskResultTabs
          onContinue={() => onComplete?.(answers)}
          prediction={resultProps.prediction}
          portfolio={resultProps.portfolio}
          shap={resultProps.shap}
          lime={resultProps.lime}
        />
      );
    }
    return null;
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