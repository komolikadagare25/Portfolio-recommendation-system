import React from "react";
import CollapsibleSection from "./CollapsibleSection";
import "./BeginnerGuide.css";

const STEPS = [
  {
    title: "1. Open a Demat & Trading account",
    body: "You need both to buy stocks in India — a Demat account holds your shares electronically, a Trading account lets you place buy/sell orders. Apps like Zerodha, Groww, or Upstox let you open both together online in about 15 minutes, using your PAN and Aadhaar for KYC.",
  },
  {
    title: "2. Complete KYC verification",
    body: "You'll upload your PAN card, address proof, a bank account for linking, and do a quick video/selfie verification. This is a one-time process required by SEBI regulations.",
  },
  {
    title: "3. Add funds to your trading account",
    body: "Transfer the amount you plan to invest (the same amount you entered in \"Build Your Portfolio\") from your bank account into your broker's trading account via UPI or net banking.",
  },
  {
    title: "4. Buy your recommended stocks",
    body: "Use the exact share counts from your Investment Plan — search each stock by name in your broker app, enter the number of shares shown, and place a \"market order\" (buys at the current live price) or a \"limit order\" (buys only at a price you set).",
  },
  {
    title: "5. Invest in the non-stock portion",
    body: "For Mutual Funds: most broker apps also let you invest directly, or use a dedicated app. For Government Bonds: look for RBI Retail Direct or bond ETFs. For Fixed Deposits: your own bank's app/branch. For Gold: consider Sovereign Gold Bonds (SGBs) or a Gold ETF instead of physical gold, for easier buying/selling.",
  },
];

const GLOSSARY = [
  { term: "Demat account", def: "Holds your shares in electronic form, like a bank account but for stocks." },
  { term: "SIP (Systematic Investment Plan)", def: "Investing a fixed amount automatically at regular intervals (e.g. monthly) instead of one lump sum — reduces the risk of bad timing." },
  { term: "Mutual Fund", def: "A pool of money from many investors, managed by professionals, spread across many stocks/bonds — an easier way to diversify than picking individual stocks yourself." },
  { term: "Government Bond", def: "You lend money to the government for a fixed period in exchange for regular interest — very low risk." },
  { term: "Gold ETF / SGB", def: "A way to invest in gold's price without physically storing gold — buy/sell like a stock." },
];

export default function BeginnerGuide() {
  return (
    <CollapsibleSection title="New to investing? Here's how to actually get started" defaultOpen={false}>
      <div className="beginner-guide">
        <p className="beginner-guide__disclaimer">
          This is general educational information, not professional financial advice.
          Markets carry risk — only invest money you can afford to have tied up.
        </p>

        <h3 className="beginner-guide__subheading">Steps to build the portfolio shown above</h3>
        <ol className="beginner-guide__steps">
          {STEPS.map((step) => (
            <li key={step.title} className="beginner-guide__step">
              <strong>{step.title}</strong>
              <p>{step.body}</p>
            </li>
          ))}
        </ol>

        <h3 className="beginner-guide__subheading">Quick glossary</h3>
        <dl className="beginner-guide__glossary">
          {GLOSSARY.map((g) => (
            <div key={g.term} className="beginner-guide__glossary-row">
              <dt>{g.term}</dt>
              <dd>{g.def}</dd>
            </div>
          ))}
        </dl>
      </div>
    </CollapsibleSection>
  );
}
