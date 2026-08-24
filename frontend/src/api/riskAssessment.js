// ============================================================================
// FRONTEND-ONLY FILE. No backend exists yet — this is the one place in the
// whole app that expects one. Everything below the config line is real,
// working frontend code (RiskAssessmentForm.jsx already calls it); it will
// throw a network error until a backend is actually running at API_BASE_URL,
// which RiskAssessmentForm.jsx already handles with its error+retry state.
//
// WHAT THE BACKEND WOULD NEED TO DO (not implemented — for reference only):
//   1. Expose POST /api/risk-assessment, accepting the questionnaire
//      `answers` object as JSON (keys match riskQuestionsReal.js ids).
//   2. Run your trained model's .predict() / .predict_proba() on those
//      answers to get a risk band + confidence.
//   3. Run a SHAP explainer (e.g. shap.TreeExplainer(model)) on the same
//      input to get per-feature contribution values.
//   4. Run a LIME explainer (e.g. lime.lime_tabular.LimeTabularExplainer)
//      on the same input to get per-feature condition + weight pairs.
//   5. Return all four pieces as one JSON object shaped exactly like the
//      @returns type below — that shape matches predictionMock.js,
//      shapMock.js, and limeMock.js field-for-field, since those mocks are
//      what every component currently renders from.
//   6. Allow CORS from the frontend's origin (e.g. http://localhost:3000),
//      since the backend will run on a different port.
// ============================================================================

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

/**
 * @param {Record<string, string|number>} answers - questionnaire answers,
 *   keyed exactly like your dataset columns (see riskQuestionsReal.js ids).
 * @returns {Promise<{
 *   prediction: { riskLevel: string, confidence: number, investmentHorizon: string, riskDescription: string, investorSummary: object },
 *   portfolio: { allocation: Array<{label:string, pct:number}>, sectors: string[], stocks: string[], advice: string },
 *   shap: { predictedBand: string, confidence: number, features: Array<{feature:string, value:number}> },
 *   lime: { predictedBand: string, confidence: number, intercept: number, localModelScore: number, features: Array<{feature:string, condition:string, weight:number}> }
 * }>}
 */
export async function fetchRiskAssessment(answers) {
  const res = await fetch(`${API_BASE_URL}/api/risk-assessment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(answers),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Risk assessment request failed (${res.status}): ${text || res.statusText}`);
  }

  return res.json();
}
