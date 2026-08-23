// Sample market data for the auth-screen ticker widget.
// Replace with a live feed (e.g. your Node/Python market-data service) when wiring up the backend.

const TICKERS = [
  {
    sym: "NIFTY50",
    val: "24,812.35",
    chg: "+1.24%",
    up: true,
    points: "0,28 15,24 30,26 45,18 60,20 75,10 90,12 105,4 120,6",
  },
  {
    sym: "RELIANCE",
    val: "2,945.10",
    chg: "+0.86%",
    up: true,
    points: "0,26 15,22 30,24 45,16 60,18 75,12 90,10 105,6 120,8",
  },
  {
    sym: "HDFCBANK",
    val: "1,680.55",
    chg: "-0.32%",
    up: false,
    points: "0,6 15,10 30,8 45,15 60,13 75,20 90,17 105,24 120,22",
  },
  {
    sym: "INFY",
    val: "1,842.90",
    chg: "+2.11%",
    up: true,
    points: "0,30 15,22 30,20 45,14 60,16 75,8 90,10 105,3 120,5",
  },
  {
    sym: "TCS",
    val: "3,910.40",
    chg: "-0.18%",
    up: false,
    points: "0,8 15,12 30,9 45,17 60,14 75,21 90,18 105,23 120,21",
  },
];

export default TICKERS;
