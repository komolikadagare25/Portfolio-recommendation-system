import React, { useState, useEffect } from "react";
import { TrendingUp, ShieldCheck } from "lucide-react";
import Sparkline from "./Sparkline";
import TICKERS from "../data/tickers";

/**
 * Left panel of the auth screen: brand mark, pitch copy, and a rotating
 * live-ticker card. This is the screen's signature visual element.
 */
export default function MarketPanel() {
  const [tickerIdx, setTickerIdx] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setTickerIdx((i) => (i + 1) % TICKERS.length);
    }, 2600);
    return () => clearInterval(interval);
  }, []);

  const ticker = TICKERS[tickerIdx];

  return (
    <div className="market-panel">
      <div className="market-panel__brand">
        <div className="market-panel__logo-row">
          <div className="market-panel__logo-mark">
            <TrendingUp size={18} strokeWidth={2.25} color="#fff" />
          </div>
          <span className="market-panel__logo-text">
            Portfolio<span className="market-panel__logo-accent">IQ</span>
          </span>
        </div>
        <p className="market-panel__tagline">AI-POWERED RECOMMENDATION ENGINE</p>
      </div>

      <div className="market-panel__pitch">
        <h2 className="market-panel__headline">
          Explainable investing,
          <br />
          built on your risk profile.
        </h2>
        <p className="market-panel__subtext">
          SHAP-backed recommendations, live risk scoring, and a portfolio
          dashboard that tells you exactly why — not just what.
        </p>
      </div>

      <div className="ticker-card">
        <div className="ticker-card__header">
          <span className="ticker-card__label">LIVE</span>
          <span className="ticker-card__status">
            <span className="ticker-card__dot" />
            MARKET OPEN
          </span>
        </div>
        <div className="ticker-card__body">
          <div>
            <p className="ticker-card__symbol">{ticker.sym}</p>
            <p className="ticker-card__value">₹{ticker.val}</p>
            <p className={`ticker-card__change ${ticker.up ? "ticker-card__change--up" : "ticker-card__change--down"}`}>
              {ticker.chg}
            </p>
          </div>
          <Sparkline points={ticker.points} up={ticker.up} />
        </div>
      </div>

      <div className="market-panel__footer">
        <ShieldCheck size={14} strokeWidth={1.75} color="#5B6478" />
        <span>256-bit encrypted · Academic demo environment</span>
      </div>
    </div>
  );
}
