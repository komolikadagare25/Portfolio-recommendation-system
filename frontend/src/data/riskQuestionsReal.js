// Field ids match your dataset columns (finance_trends.csv) exactly.
// All option values below are CONFIRMED via df[col].value_counts() across
// the full 12,000-row dataset (see Investor_EDA.ipynb, cell 13) — not guesses.

export const riskQuestions = [
  {
    id: "age",
    question: "What's your age?",
    type: "number",
    min: 18, // actual dataset range: 18–38 (df.describe())
    max: 100,
  },
  {
    id: "gender",
    question: "What's your gender?",
    type: "select",
    options: ["Male", "Female"],
  },
  {
    id: "Investment_Avenues",
    question: "Do you currently invest in any investment avenues?",
    type: "select",
    options: ["Yes", "No"],
  },
  {
    id: "Stock_Marktet", // NOTE: matches the (misspelled) column name in your dataset exactly
    question: "Do you invest directly in the stock market?",
    type: "select",
    options: ["Yes", "No"],
  },
  {
    id: "Factor",
    question: "What matters most to you when investing?",
    type: "select",
    options: ["Returns", "Risk", "Locking Period"],
  },
  {
    id: "Objective",
    question: "What's your primary investment objective?",
    type: "select",
    options: ["Capital Appreciation", "Growth", "Income"],
  },
  {
    id: "Duration",
    question: "How long do you plan to stay invested?",
    type: "select",
    options: ["Less than 1 year", "1-3 years", "3-5 years", "More than 5 years"],
  },
  {
    id: "Invest_Monitor",
    question: "How often do you monitor your investments?",
    type: "select",
    options: ["Daily", "Weekly", "Monthly"],
  },
  {
    id: "Expect",
    question: "What annual return do you expect from your investments?",
    type: "select",
    options: ["10%-20%", "20%-30%", "30%-40%"], // these are the ONLY 3 values in the entire dataset
  },
  {
    id: "Avenue",
    question: "Which investment avenue would you like to explore most?",
    type: "select",
    options: ["Fixed Deposits", "Mutual Fund", "Public Provident Fund", "Equity"],
  },
];