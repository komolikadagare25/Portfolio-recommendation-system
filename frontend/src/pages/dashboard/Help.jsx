import React, { useState } from "react";
import { Mail, CheckCircle2, AlertTriangle } from "lucide-react";
import CollapsibleSection from "../../dashboard/widgets/RiskAssessment/CollapsibleSection";
import "./Help.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";
const SUPPORT_EMAIL = "support@portfolioiq.app";

const FAQS = [
  {
    q: "How does PortfolioIQ decide my risk band?",
    a: "A model trained on your questionnaire answers — things like age, investment horizon, income, and loss tolerance — predicts whether you're Conservative, Moderate, or Aggressive. You can see exactly which answers drove that decision under \"Want the technical detail behind your risk classification?\" on the Recommendations page.",
  },
  {
    q: "How often should I retake the Risk Assessment?",
    a: "Whenever something material changes — income, goals, time horizon, or how you feel about risk after living through a downturn. Otherwise, roughly once a year is a reasonable cadence. You can retake it any time from Settings.",
  },
  {
    q: "Are the stock recommendations financial advice?",
    a: "No. They're generated from your stated risk profile and general market data, meant as a starting point for your own research — not personalized financial advice from a licensed advisor. See the disclaimer in \"New to investing?\" on the Recommendations page for more.",
  },
  {
    q: "Where do the live prices in \"Build Your Portfolio\" come from?",
    a: "When you enter an amount on the My Portfolio page, we fetch current market prices for your recommended stocks to calculate exactly how many shares you could buy today.",
  },
  {
    q: "Can I change my recommended sectors or stocks manually?",
    a: "Not directly yet — recommendations are generated from your risk profile. If you want a different mix, retaking the assessment with adjusted answers (like your stated risk sliders) will shift the output.",
  },
];

const GLOSSARY = [
  { term: "SHAP", def: "A method that shows how much each answer in your questionnaire pushed the model's decision toward — or away from — your predicted risk band." },
  { term: "LIME", def: "A second, independent method for explaining the same prediction, useful for cross-checking the SHAP explanation against a different technique." },
  { term: "Risk band", def: "Your overall risk classification — Conservative, Moderate, or Aggressive — based on how much volatility you're likely comfortable with." },
  { term: "Diversification", def: "Spreading investments across different sectors or asset types so no single one can sink your whole portfolio." },
  { term: "Confidence", def: "How certain the model is in its risk band prediction, expressed as a percentage — lower confidence means your answers sat closer to a boundary between two bands." },
  { term: "Asset allocation", def: "The percentage split of your recommended portfolio across categories like Stocks, Mutual Funds, Government Bonds, Fixed Deposits, and Gold." },
  { term: "XIRR", def: "A return metric that accounts for the exact timing and size of each investment, useful when you've added money at different points rather than all at once." },
];

export default function Help() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState(null); // { type, message }

  const token = localStorage.getItem("access_token");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus(null);
    setSending(true);
    try {
      const res = await fetch(`${API_BASE_URL}/support`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ name, email, message }),
      });
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      setStatus({ type: "success", message: "Message sent — we'll get back to you soon." });
      setName("");
      setEmail("");
      setMessage("");
    } catch (err) {
      setStatus({
        type: "error",
        message: `Couldn't send that — email us directly at ${SUPPORT_EMAIL} instead.`,
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="help-page">
      <div className="help-page__header">
        <h1>Help</h1>
        <p>Answers to common questions, a glossary of terms used across the app, and how to reach us.</p>
      </div>

      <section className="help-panel">
        <h2 className="help-panel__title">Frequently asked questions</h2>
        <div className="help-faq-list">
          {FAQS.map((faq) => (
            <CollapsibleSection key={faq.q} title={faq.q} defaultOpen={false}>
              <p className="help-faq-answer">{faq.a}</p>
            </CollapsibleSection>
          ))}
        </div>
      </section>

      <section className="help-panel">
        <h2 className="help-panel__title">Glossary</h2>
        <dl className="help-glossary">
          {GLOSSARY.map((g) => (
            <div key={g.term} className="help-glossary__row">
              <dt>{g.term}</dt>
              <dd>{g.def}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="help-panel">
        <h2 className="help-panel__title">Still need help?</h2>
        <p className="help-panel__subtext">
          Send us a message and we'll get back to you, or email{" "}
          <a href={`mailto:${SUPPORT_EMAIL}`} className="help-mail-link">{SUPPORT_EMAIL}</a> directly.
        </p>

        <form className="help-contact-form" onSubmit={handleSubmit}>
          <div className="help-contact-form__row">
            <label htmlFor="help-name">Name</label>
            <input id="help-name" type="text" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="help-contact-form__row">
            <label htmlFor="help-email">Email</label>
            <input id="help-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="help-contact-form__row">
            <label htmlFor="help-message">Message</label>
            <textarea id="help-message" rows={4} value={message} onChange={(e) => setMessage(e.target.value)} required />
          </div>

          {status && (
            <p className={`help-status help-status--${status.type}`}>
              {status.type === "success" ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
              {status.message}
            </p>
          )}

          <button type="submit" className="help-submit-btn" disabled={sending}>
            <Mail size={15} strokeWidth={2} />
            {sending ? "Sending…" : "Send message"}
          </button>
        </form>
      </section>
    </div>
  );
}
