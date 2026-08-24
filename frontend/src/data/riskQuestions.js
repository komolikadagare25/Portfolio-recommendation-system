// Matches the backend's canonical field/option constants exactly (as provided).
// Casing here follows the backend code, NOT the raw CSV — e.g. "Less Than 1 Year"
// here vs "Less than 1 year" in the raw dataset. Verify there's a normalization
// step between this API layer and whatever the model was actually trained on.

const GENDER_OPTIONS = ["Female", "Male"];
const YES_NO_OPTIONS = ["Yes", "No"];
const FACTOR_OPTIONS = ["Returns", "Risk", "Locking Period"];
const OBJECTIVE_OPTIONS = ["Growth", "Capital Appreciation", "Income"];
const PURPOSE_OPTIONS = ["Wealth Creation", "Returns", "Savings For Future"];
const DURATION_OPTIONS = ["Less Than 1 Year", "1-3 Years", "3-5 Years", "More Than 5 Years"];
const INVEST_MONITOR_OPTIONS = ["Daily", "Weekly", "Monthly"];
const EXPECT_OPTIONS = ["10%-20%", "20%-30%", "30%-40%"];
const AVENUE_OPTIONS = ["Mutual Fund", "Equity", "Fixed Deposits", "Public Provident Fund"];
const SAVINGS_OBJECTIVE_OPTIONS = ["Retirement Plan", "Health Care", "Education"];
const REASON_EQUITY_OPTIONS = ["Capital Appreciation", "Dividend", "Liquidity"];
const REASON_MUTUAL_OPTIONS = ["Better Returns", "Fund Diversification", "Tax Benefits"];
const REASON_BONDS_OPTIONS = ["Assured Returns", "Safe Investment", "Tax Incentives"];
const REASON_FD_OPTIONS = ["Fixed Returns", "High Interest Rates", "Risk Free"];
const SOURCE_OPTIONS = ["Internet", "Television", "Newspapers And Magazines", "Financial Consultants"];

export const riskQuestions = [
  {
    id: "age",
    question: "What's your age?",
    type: "number",
    min: 18,
    max: 100,
  },
  {
    id: "gender",
    question: "What's your gender?",
    type: "select",
    options: GENDER_OPTIONS,
  },
  {
    id: "Investment_Avenues",
    question: "Do you currently invest in any investment avenues?",
    type: "select",
    options: YES_NO_OPTIONS,
  },
  {
    id: "Stock_Marktet", // matches the (misspelled) column name in the dataset exactly
    question: "Do you invest directly in the stock market?",
    type: "select",
    options: YES_NO_OPTIONS,
  },
  {
    id: "investment_preferences",
    question: "Rate how much you prefer each investment avenue (1 = least, 7 = most preferred)",
    type: "slider-group",
    fields: [
      { id: "Mutual_Funds", label: "Mutual Funds", min: 1, max: 5, default: 4 },
      { id: "Equity_Market", label: "Equity Market", min: 1, max: 5, default: 4 },
      { id: "Debentures", label: "Debentures", min: 1, max: 5, default: 4 },
      { id: "Government_Bonds", label: "Government Bonds", min: 1, max: 5, default: 4 },
      { id: "Fixed_Deposits", label: "Fixed Deposits", min: 1, max: 5, default: 4 },
      { id: "PPF", label: "PPF", min: 1, max: 5, default: 4 },
      { id: "Gold", label: "Gold", min: 1, max: 5, default: 4 },
    ],
  },
  {
    id: "Factor",
    question: "What matters most to you when investing?",
    type: "select",
    options: FACTOR_OPTIONS,
  },
  {
    id: "Objective",
    question: "What's your primary investment objective?",
    type: "select",
    options: OBJECTIVE_OPTIONS,
  },
  {
    id: "Purpose",
    question: "What's the underlying purpose of this investment?",
    type: "select",
    options: PURPOSE_OPTIONS,
  },
  {
    id: "Duration",
    question: "How long do you plan to stay invested?",
    type: "select",
    options: DURATION_OPTIONS,
  },
  {
    id: "Invest_Monitor",
    question: "How often do you monitor your investments?",
    type: "select",
    options: INVEST_MONITOR_OPTIONS,
  },
  {
    id: "Expect",
    question: "What annual return do you expect from your investments?",
    type: "select",
    options: EXPECT_OPTIONS,
  },
  {
    id: "Avenue",
    question: "Which investment avenue would you like to explore most?",
    type: "select",
    options: AVENUE_OPTIONS,
  },
  {
    id: "Savings_Objective", 
    question: "What are your savings objectives?",
    type: "select",
    options: SAVINGS_OBJECTIVE_OPTIONS,
  },
  {
    id: "Reason_Equity",
    question: "If you invest in equity, what's the main reason?",
    type: "select",
    options: REASON_EQUITY_OPTIONS,
  },
  {
    id: "Reason_Mutual",
    question: "If you invest in mutual funds, what's the main reason?",
    type: "select",
    options: REASON_MUTUAL_OPTIONS,
  },
  {
    id: "Reason_Bonds",
    question: "If you invest in bonds, what's the main reason?",
    type: "select",
    options: REASON_BONDS_OPTIONS,
  },
  {
    id: "Reason_FD",
    question: "If you invest in fixed deposits, what's the main reason?",
    type: "select",
    options: REASON_FD_OPTIONS,
  },
  {
    id: "Source",
    question: "Where do you usually get your financial information from?",
    type: "select",
    options: SOURCE_OPTIONS,
  },
];
