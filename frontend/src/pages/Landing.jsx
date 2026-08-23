import Navbar from "../includes/Navbar";
import Footer from "../includes/Footer";
import "./Landing.css";

function Landing() {
  return (
    <div className="landing-page">

      <Navbar />

      <main className="landing-content">

        <div className="landing-text">

          <p className="landing-tag">
            AI POWERED PORTFOLIO RECOMMENDATION
          </p>

          <h1>
            Explainable investing,
            <br />
            built around your risk profile.
          </h1>

          <p className="landing-desc">
            Get personalized stock recommendations using machine learning,
            risk analysis and explainable AI techniques.
          </p>

          <div className="landing-buttons">
            <button className="primary-btn">
              Get Started
            </button>

            <button className="secondary-btn">
              Learn More
            </button>
          </div>

        </div>


        <div className="landing-card">

          <h3>PortfolioIQ</h3>

          <p>
            ML-based recommendations with SHAP explainability
          </p>

          <div className="stats">

            <div>
              <span>AI</span>
              <p>Powered</p>
            </div>

            <div>
              <span>Risk</span>
              <p>Analyzed</p>
            </div>

            <div>
              <span>SHAP</span>
              <p>Explained</p>
            </div>

          </div>

        </div>


      </main>


      <Footer />

    </div>
  );
}

export default Landing;