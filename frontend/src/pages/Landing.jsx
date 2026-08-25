import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import "./Landing.css";
import Navbar from "../includes/Navbar";
import Footer from "../includes/Footer";

const pipeline = [
  {
    number: "01",
    title: "Market Data",
    text: "Collect relevant financial and portfolio data.",
  },
  {
    number: "02",
    title: "Preprocessing",
    text: "Clean and transform the incoming data.",
  },
  {
    number: "03",
    title: "Feature Engineering",
    text: "Extract meaningful signals from the data.",
  },
  {
    number: "04",
    title: "ML Analysis",
    text: "The model evaluates portfolio compatibility and risk.",
  },
  {
    number: "05",
    title: "Explainability",
    text: "SHAP and LIME help explain the model's predictions.",
  },
  {
    number: "06",
    title: "Insights",
    text: "Turn model output into understandable decisions.",
  },
];

export default function Landing() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % pipeline.length);
    }, 1800);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="home-page">

      {/* NAVBAR */}
      {/* <nav className="home-navbar">
        <Link to="/" className="home-logo">
          <span className="logo-mark">◈</span>
          <span>Porta<span>lytics</span></span>
        </Link>

        <div className="nav-links">
          <Link to="/" className="active">Home</Link>
          <a href="#how-it-works">How It Works</a>
          <Link to="/design">System Design</Link>
          <a href="#insights">Insights</a>
        </div>

        <Link to="/analyzer" className="nav-button">
          Get Started
          <span>↗</span>
        </Link>
      </nav> */}

      <Navbar />


      {/* HERO */}
      <section className="hero-section">

        <div className="hero-content">

          <div className="hero-label">
            <span className="pulse-dot"></span>
            AI-POWERED PORTFOLIO INTELLIGENCE
          </div>

          <h1>
            Turn your portfolio
            <br />
            into <span>intelligent</span>
            <br />
            decisions.
          </h1>

          <p className="hero-description">
            Analyze portfolio compatibility, understand risk,
            and discover what drives your results with
            explainable machine learning.
          </p>

          <div className="hero-actions">
            <Link to="/login" className="primary-button">
              Analyze Portfolio
              <span>→</span>
            </Link>

            <Link to="/design" className="secondary-button">
              Explore System
              <span>↗</span>
            </Link>
          </div>

          <div className="hero-meta">
            <div>
              <strong>ML</strong>
              <span>Powered Analysis</span>
            </div>

            <div className="meta-line"></div>

            <div>
              <strong>XAI</strong>
              <span>Explainable Results</span>
            </div>

            <div className="meta-line"></div>

            <div>
              <strong>Real-time</strong>
              <span>Market Data</span>
            </div>
          </div>

        </div>


        {/* HERO VISUAL */}
        <div className="hero-visual">

          <div className="visual-grid"></div>

          <div className="data-orbit orbit-one"></div>
          <div className="data-orbit orbit-two"></div>

          <div className="floating-label label-top">
            <span></span>
            LIVE ANALYSIS
          </div>

          <div className="ai-core">

            <div className="core-ring ring-one"></div>
            <div className="core-ring ring-two"></div>

            <div className="core-center">
              <span className="core-symbol">◈</span>
              <small>AI ENGINE</small>
            </div>

          </div>


          <div className="data-node node-one">
            <span className="node-dot"></span>
            <div>
              <small>INPUT</small>
              <strong>Market Data</strong>
            </div>
          </div>

          <div className="data-node node-two">
            <span className="node-dot"></span>
            <div>
              <small>MODEL</small>
              <strong>Random Forest</strong>
            </div>
          </div>

          <div className="data-node node-three">
            <span className="node-dot"></span>
            <div>
              <small>OUTPUT</small>
              <strong>Risk 72%</strong>
            </div>
          </div>


          <div className="connection connection-one"></div>
          <div className="connection connection-two"></div>
          <div className="connection connection-three"></div>

        </div>

      </section>


      {/* SCROLL INDICATOR */}
      <div className="scroll-indicator">
        <span>SCROLL TO EXPLORE</span>
        <div className="scroll-line"></div>
      </div>


      {/* HOW IT WORKS */}
      <section id="how-it-works" className="process-section">

        <div className="section-heading">

          <div className="section-number">01 / PROCESS</div>

          <h2>
            From raw data
            <br />
            to <span>clear insight.</span>
          </h2>

          <p>
            Every prediction passes through a structured pipeline
            designed to transform complex financial data into
            understandable results.
          </p>

        </div>


        <div className="pipeline">

          <div className="pipeline-line">
            <div
              className="pipeline-progress"
              style={{
                height: `${((activeStep + 1) / pipeline.length) * 100}%`,
              }}
            ></div>
          </div>

          {pipeline.map((item, index) => (

            <div
              className={`pipeline-step ${
                activeStep === index ? "active" : ""
              }`}
              key={item.number}
              onMouseEnter={() => setActiveStep(index)}
            >

              <div className="step-number">
                {item.number}
              </div>

              <div className="step-content">

                <h3>{item.title}</h3>

                <p>{item.text}</p>

              </div>

              <div className="step-status">
                {activeStep === index ? "PROCESSING" : "○"}
              </div>

            </div>

          ))}

        </div>

        <Link to="/design" className="process-link">
          See the complete system architecture
          <span>→</span>
        </Link>

      </section>


      {/* INSIGHTS */}
      <section id="insights" className="insights-section">

        <div className="insight-header">

          <div>
            <div className="section-number">02 / OUTPUT</div>

            <h2>
              Numbers are useful.
              <br />
              <span>Understanding is better.</span>
            </h2>
          </div>

          <p>
            The system doesn't just provide a prediction.
            It helps explain what influenced that prediction.
          </p>

        </div>


        <div className="insight-visual">

          <div className="insight-center">

            <div className="score-circle">
              <span>86</span>
              <small>%</small>
            </div>

            <p>PORTFOLIO COMPATIBILITY</p>

          </div>


          <div className="insight-item insight-left">
            <span>01</span>
            <div>
              <strong>Risk Analysis</strong>
              <small>Understand exposure</small>
            </div>
          </div>

          <div className="insight-item insight-right">
            <span>02</span>
            <div>
              <strong>Compatibility</strong>
              <small>Measure portfolio fit</small>
            </div>
          </div>

          <div className="insight-item insight-bottom">
            <span>03</span>
            <div>
              <strong>Explainability</strong>
              <small>Know why the model decided</small>
            </div>
          </div>

        </div>

      </section>


      {/* CTA */}
      <section className="cta-section">

        <div className="cta-glow"></div>

        <div className="cta-content">

          <div className="section-number">03 / START</div>

          <h2>
            Ready to understand
            <br />
            your <span>portfolio?</span>
          </h2>

          <p>
            Let the system turn your data into insights
            you can actually understand.
          </p>

          <Link to="/login" className="primary-button large">
            Start Analysis
            <span>→</span>
          </Link>

        </div>

      </section>


      {/* FOOTER */}
      {/* <footer className="home-footer">

        <div className="footer-brand">
          <span className="logo-mark">◈</span>
          <strong>Portalytics</strong>
        </div>

        <p>
          Intelligent portfolio analysis powered by machine learning.
        </p>

        <div className="footer-links">
          <Link to="/">Home</Link>
          <Link to="/design">System Design</Link>
          <Link to="/login">Analyzer</Link>
        </div>

        <span className="copyright">
          © 2026 Portalytics
        </span>

      </footer> */}
      <Footer />

    </div>
  );
}