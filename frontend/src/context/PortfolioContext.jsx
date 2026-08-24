import React, { createContext, useContext, useState } from "react";

const PortfolioContext = createContext(null);

// Same localStorage key everywhere, so a page refresh on /dashboard/portfolio
// doesn't lose the last prediction (the backend has no "get my last result"
// endpoint yet, so this is the stand-in for that until it does).
const STORAGE_KEY = "portfolioiq_last_result";

function readStoredResult() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/**
 * Holds the most recent /api/risk-assessment response
 * ({ prediction, portfolio, shap, lime } — see api/riskAssessment.js) so any
 * page (My Portfolio, Dashboard Home, etc.) can read it, not just the
 * Risk Assessment form that produced it.
 */
export function PortfolioProvider({ children }) {
  const [result, setResultState] = useState(readStoredResult);

  const setResult = (data) => {
    setResultState(data);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch {
      // localStorage can fail (private mode, quota) — not fatal, just means
      // a refresh won't remember the result.
    }
  };

  const clearResult = () => {
    setResultState(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
  };

  return (
    <PortfolioContext.Provider value={{ result, setResult, clearResult, hasResult: !!result }}>
      {children}
    </PortfolioContext.Provider>
  );
}

export function usePortfolio() {
  return useContext(PortfolioContext);
}
