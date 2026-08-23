const GENDER_OPTIONS = ["Female", "Male"];

const YES_NO_OPTIONS = ["Yes", "No"];

const FACTOR_OPTIONS = [
  "Returns",
  "Risk",
  "Locking Period",
];

const OBJECTIVE_OPTIONS = [
  "Growth",
  "Capital Appreciation",
  "Income",
];

const PURPOSE_OPTIONS = [
  "Wealth Creation",
  "Returns",
  "Savings For Future",
];

const DURATION_OPTIONS = [
  "Less Than 1 Year",
  "1-3 Years",
  "3-5 Years",
  "More Than 5 Years",
];

const INVEST_MONITOR_OPTIONS = [
  "Daily",
  "Weekly",
  "Monthly",
];

const EXPECT_OPTIONS = [
  "10%-20%",
  "20%-30%",
  "30%-40%",
];

const AVENUE_OPTIONS = [
  "Mutual Fund",
  "Equity",
  "Fixed Deposits",
  "Public Provident Fund",
];

const SAVINGS_OBJECTIVE_OPTIONS = [
  "Retirement Plan",
  "Health Care",
  "Education",
];

const REASON_EQUITY_OPTIONS = [
  "Capital Appreciation",
  "Dividend",
  "Liquidity",
];

const REASON_MUTUAL_OPTIONS = [
  "Better Returns",
  "Fund Diversification",
  "Tax Benefits",
];

const REASON_BONDS_OPTIONS = [
  "Assured Returns",
  "Safe Investment",
  "Tax Incentives",
];

const REASON_FD_OPTIONS = [
  "Fixed Returns",
  "High Interest Rates",
  "Risk Free",
];

const SOURCE_OPTIONS = [
  "Internet",
  "Television",
  "Newspapers And Magazines",
  "Financial Consultants",
];

export const riskQuestions = [
  {
    id: "age",
    question: "What's your age?",
    type: "number",
    min: 18,
    max: 38,
    required: true,
  },

  {
    id: "gender",
    question: "What's your gender?",
    type: "select",
    options: GENDER_OPTIONS,
    required: true,
  },

  {
    id: "Investment_Avenues",
    question: "Do you currently invest in any investment avenues?",
    type: "select",
    options: YES_NO_OPTIONS,
    required: true,
  },

  {
    id: "Stock_Marktet",
    question: "Do you invest directly in the stock market?",
    type: "select",
    options: YES_NO_OPTIONS,
    required: true,
  },

  {
    id: "Factor",
    question: "What matters most to you when investing?",
    type: "select",
    options: FACTOR_OPTIONS,
    required: true,
  },

  {
    id: "Objective",
    question: "What's your primary investment objective?",
    type: "select",
    options: OBJECTIVE_OPTIONS,
    required: true,
  },

  {
    id: "Purpose",
    question: "What's the underlying purpose of this investment?",
    type: "select",
    options: PURPOSE_OPTIONS,
    required: true,
  },

  {
    id: "Duration",
    question: "How long do you plan to stay invested?",
    type: "select",
    options: DURATION_OPTIONS,
    required: true,
  },

  {
    id: "Invest_Monitor",
    question: "How often do you monitor your investments?",
    type: "select",
    options: INVEST_MONITOR_OPTIONS,
    required: true,
  },

  {
    id: "Expect",
    question: "What annual return do you expect from your investments?",
    type: "select",
    options: EXPECT_OPTIONS,
    required: true,
  },

  {
    id: "Avenue",
    question: "Which investment avenue would you like to explore most?",
    type: "select",
    options: AVENUE_OPTIONS,
    required: true,
  },

  {
    id: "Savings_Objective",
    question: "What are your savings objectives?",
    type: "select",
    options: SAVINGS_OBJECTIVE_OPTIONS,
    required: true,
  },

  {
    id: "Reason_Equity",
    question: "If you invest in equity, what's the main reason?",
    type: "select",
    options: REASON_EQUITY_OPTIONS,
    required: false,
  },

  {
    id: "Reason_Mutual",
    question: "If you invest in mutual funds, what's the main reason?",
    type: "select",
    options: REASON_MUTUAL_OPTIONS,
    required: false,
  },

  {
    id: "Reason_Bonds",
    question: "If you invest in bonds, what's the main reason?",
    type: "select",
    options: REASON_BONDS_OPTIONS,
    required: false,
  },

  {
    id: "Reason_FD",
    question: "If you invest in fixed deposits, what's the main reason?",
    type: "select",
    options: REASON_FD_OPTIONS,
    required: false,
  },

  {
    id: "Source",
    question: "Where do you usually get your financial information from?",
    type: "select",
    options: SOURCE_OPTIONS,
    required: true,
  },
];

export default riskQuestions;