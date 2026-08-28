import React, { useEffect, useState } from "react";
import Navbar from "../includes/Navbar";
import Footer from "../includes/Footer";
import "./SystemDesign.css";

const STEPS = [
  {
    id: "input",
    number: 1,
    label: "USER INPUT",
    title: "User submits financial profile",
    description:
      "The React frontend collects the user's financial information, investment preferences, risk tolerance and other assessment inputs.",
    tech: "React.js",
    type: "start",
  },
  {
    id: "api",
    number: 2,
    label: "API LAYER",
    title: "Request reaches Express.js API",
    description:
      "The frontend sends the assessment data to the backend through a REST API request.",
    tech: "Node.js + Express.js",
    type: "normal",
  },
  {
    id: "validation",
    number: 3,
    label: "VALIDATION",
    title: "Validate incoming data",
    description:
      "Joi checks required fields, data types and acceptable value ranges before the request enters the ML pipeline.",
    tech: "Joi Schema",
    type: "normal",
  },
  {
    id: "decision",
    number: 4,
    label: "DECISION",
    title: "Are the inputs valid?",
    description:
      "The backend decides whether the submitted data satisfies all validation rules.",
    tech: "Validation Gate",
    type: "decision",
  },
  {
    id: "ml",
    number: 5,
    label: "ML PIPELINE",
    title: "Classify investor risk",
    description:
      "The validated features are passed to the Random Forest model to determine the user's risk profile and confidence score.",
    tech: "Python + Flask + Random Forest",
    type: "normal",
  },
  {
    id: "scoring",
    number: 6,
    label: "SCORING ENGINE",
    title: "Score available stocks",
    description:
      "Stocks are evaluated using factors such as return, volatility, Sharpe ratio and sector diversification.",
    tech: "Portfolio Scoring",
    type: "normal",
  },
  {
    id: "explain",
    number: 7,
    label: "EXPLAINABILITY",
    title: "Explain the prediction",
    description:
      "SHAP explains the global feature contribution while LIME provides local rules explaining the individual recommendation.",
    tech: "SHAP + LIME",
    type: "parallel",
  },
  {
    id: "assemble",
    number: 8,
    label: "AGGREGATION",
    title: "Build final recommendation",
    description:
      "Risk classification, stock scores and explainability results are combined into one personalized recommendation.",
    tech: "Recommendation Engine",
    type: "normal",
  },
  {
    id: "database",
    number: 9,
    label: "DATABASE",
    title: "Persist recommendation",
    description:
      "The generated portfolio, assessment information and explanation data are stored for later retrieval.",
    tech: "MongoDB",
    type: "normal",
  },
  {
    id: "frontend",
    number: 10,
    label: "PRESENTATION",
    title: "Render personalized dashboard",
    description:
      "React retrieves the processed result and displays the portfolio, charts, stock information and AI explanations.",
    tech: "React.js",
    type: "normal",
  },
  {
    id: "result",
    number: 11,
    label: "OUTPUT",
    title: "Personalized portfolio displayed",
    description:
      "The user receives a portfolio recommendation together with understandable AI-driven explanations.",
    tech: "Final Result",
    type: "end",
  },
];

export default function SystemDesignFlow() {
  const [currentStep, setCurrentStep] = useState(0);
  const [branch, setBranch] = useState(null);
  const [showExplanation, setShowExplanation] = useState(true);

  const isFinished = currentStep >= STEPS.length - 1;

  const current = STEPS[currentStep];

  const handleNext = () => {
    if (current.id === "decision" && !branch) {
      return;
    }

    if (currentStep < STEPS.length - 1) {
      setCurrentStep((prev) => prev + 1);
      setShowExplanation(true);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);

      if (currentStep <= 4) {
        setBranch(null);
      }

      setShowExplanation(true);
    }
  };

  const handleReset = () => {
    setCurrentStep(0);
    setBranch(null);
    setShowExplanation(true);
  };

  const chooseBranch = (value) => {
    setBranch(value);

    if (value === "yes") {
      setCurrentStep(4);
    } else {
      setShowExplanation(true);
    }
  };

  useEffect(() => {
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }, []);

  return (
    <>
      <Navbar />

      <main className="system-page">
        {/* HERO */}
        <section className="system-hero">
          <div className="hero-kicker">SYSTEM DESIGN</div>

          <h1>
            From financial data
            <span> to portfolio recommendation.</span>
          </h1>

          <p>
            Follow the data as it moves through validation, machine learning,
            explainability, scoring and finally reaches the user's dashboard.
          </p>
        </section>

        {/* FLOW CONTROLS */}
        <section className="flow-section">
          <div className="flow-header">
            <div>
              <span className="flow-label">LIVE DATA FLOW</span>

              <h2>
                How the system processes
                <span> your data</span>
              </h2>
            </div>

            <div className="step-counter">
              <strong>{String(currentStep + 1).padStart(2, "0")}</strong>
              <span>/ {String(STEPS.length).padStart(2, "0")}</span>
            </div>
          </div>

          {/* TREE */}
          <div className="tree-wrapper">
            <div className="tree">

              {STEPS.map((step, index) => {
                const isVisible = index <= currentStep;
                const isActive = index === currentStep;
                const isPast = index < currentStep;

                if (!isVisible) return null;

                return (
                  <React.Fragment key={step.id}>

                    {/* CONNECTOR */}
                    {index > 0 && (
                      <div
                        className={`tree-connector ${
                          isPast ? "connector-active" : ""
                        }`}
                      >
                        <span />
                      </div>
                    )}

                    {/* NODE */}
                    <div
                      className={`tree-node ${
                        isActive ? "node-active" : ""
                      } ${isPast ? "node-past" : ""}`}
                    >
                      <div className="node-line">
                        <div className="node-marker">
                          {step.type === "decision" ? (
                            <div className="decision-shape">?</div>
                          ) : (
                            <span>{step.number}</span>
                          )}
                        </div>

                        <div className="node-content">
                          <div className="node-meta">
                            <span>{step.label}</span>

                            {isPast && (
                              <span className="completed">
                                ✓ COMPLETED
                              </span>
                            )}
                          </div>

                          <h3>{step.title}</h3>

                          {isActive && (
                            <>
                              <div
                                className={`node-description ${
                                  showExplanation ? "description-show" : ""
                                }`}
                              >
                                {step.description}
                              </div>

                              <div className="tech-line">
                                <span className="tech-dot" />
                                {step.tech}
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* DECISION BRANCH */}
                    {step.id === "decision" && isActive && (
                      <div className="decision-branches">

                        <button
                          className={`branch branch-yes ${
                            branch === "yes" ? "branch-selected" : ""
                          }`}
                          onClick={() => chooseBranch("yes")}
                        >
                          <span className="branch-symbol">✓</span>

                          <div>
                            <strong>YES — Valid</strong>
                            <small>
                              Continue to ML pipeline
                            </small>
                          </div>
                        </button>

                        <div className="branch-divider">
                          <span>OR</span>
                        </div>

                        <button
                          className={`branch branch-no ${
                            branch === "no" ? "branch-selected" : ""
                          }`}
                          onClick={() => chooseBranch("no")}
                        >
                          <span className="branch-symbol">×</span>

                          <div>
                            <strong>NO — Invalid</strong>
                            <small>
                              Return validation error
                            </small>
                          </div>
                        </button>
                      </div>
                    )}

                    {/* ERROR PATH */}
                    {step.id === "decision" && branch === "no" && (
                      <div className="error-path">
                        <div className="error-line" />

                        <div className="error-node">
                          <div className="error-marker">!</div>

                          <div>
                            <span>ERROR HANDLER</span>
                            <h3>400 — Invalid request</h3>
                            <p>
                              The frontend highlights the invalid fields and
                              asks the user to correct the input before
                              submitting again.
                            </p>
                          </div>
                        </div>

                        <div className="error-end">
                          <span>FLOW STOPS</span>
                        </div>
                      </div>
                    )}

                    {/* PARALLEL SHAP / LIME */}
                    {step.id === "explain" && isActive && (
                      <div className="parallel-flow">

                        <div className="parallel-branch">
                          <div className="parallel-marker">SHAP</div>

                          <h4>Global explanation</h4>

                          <p>
                            Shows which features had the strongest influence
                            on the model's prediction.
                          </p>

                          <div className="mini-value">
                            Horizon <strong>+0.42</strong>
                          </div>

                          <div className="mini-value">
                            Savings <strong>+0.35</strong>
                          </div>
                        </div>

                        <div className="parallel-center">
                          <span>+</span>
                        </div>

                        <div className="parallel-branch">
                          <div className="parallel-marker lime">
                            LIME
                          </div>

                          <h4>Local explanation</h4>

                          <p>
                            Explains why this particular user received this
                            particular prediction.
                          </p>

                          <div className="mini-value">
                            Dependents <strong>-0.31</strong>
                          </div>

                          <div className="mini-value">
                            EMI <strong>-0.20</strong>
                          </div>
                        </div>

                      </div>
                    )}
                  </React.Fragment>
                );
              })}

            </div>
          </div>

          {/* EXPLANATION PANEL */}
          <div className="process-explanation">
            <div className="explanation-number">
              {String(currentStep + 1).padStart(2, "0")}
            </div>

            <div className="explanation-content">
              <span>WHAT IS HAPPENING?</span>

              <p>{current.description}</p>
            </div>
          </div>

          {/* CONTROLS */}
          <div className="flow-controls">

            <button
              className="control secondary"
              onClick={handlePrevious}
              disabled={currentStep === 0}
            >
              ← Previous
            </button>

            <button
              className="control reset"
              onClick={handleReset}
            >
              ↻ Restart
            </button>

            {!isFinished && current.id !== "decision" && (
              <button
                className="control primary"
                onClick={handleNext}
              >
                Next Step
                <span>→</span>
              </button>
            )}

            {current.id === "decision" && !branch && (
              <div className="choose-hint">
                Choose a path above
              </div>
            )}

            {isFinished && (
              <button
                className="control primary"
                onClick={handleReset}
              >
                Run Again
                <span>↻</span>
              </button>
            )}
          </div>
        </section>

        {/* SUMMARY */}
        <section className="architecture-summary">
          <div className="summary-line" />

          <span className="flow-label">SYSTEM SUMMARY</span>

          <h2>
            One request.
            <span> Multiple intelligent stages.</span>
          </h2>

          <p>
            The system separates data collection, validation, prediction,
            scoring, explainability, storage and presentation into clear
            processing stages.
          </p>

          <div className="summary-flow">
            <span>React</span>
            <i>→</i>
            <span>Express</span>
            <i>→</i>
            <span>Validation</span>
            <i>→</i>
            <span>Random Forest</span>
            <i>→</i>
            <span>SHAP / LIME</span>
            <i>→</i>
            <span>MongoDB</span>
            <i>→</i>
            <span>Dashboard</span>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}