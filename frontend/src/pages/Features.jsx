import { Link } from "react-router-dom";
import {
  Brain,
  ShieldCheck,
  LineChart,
  PieChart,
  Sparkles,
  LayoutDashboard,
  User,
  Code2,
  Server,
  Cpu,
  ArrowRight,
} from "lucide-react";

import Navbar from "../includes/Navbar";
import Footer from "../includes/Footer";
import "./Features.css";

const FEATURES = [
  {
    icon: ShieldCheck,
    title: "Risk Profiling Questionnaire",
    description:
      "A short, guided questionnaire covering your age, goals, and investment preferences to understand exactly how much risk you're comfortable with.",
  },
  {
    icon: Brain,
    title: "ML-Powered Risk Prediction",
    description:
      "A Random Forest model trained on real investor data classifies you as Conservative, Moderate, or Aggressive — with a confidence score attached.",
  },
  {
    icon: Sparkles,
    title: "Explainable AI (SHAP & LIME)",
    description:
      "Every prediction comes with a plain-language breakdown of exactly which answers pushed it one way or another — no black-box guessing.",
  },
  {
    icon: PieChart,
    title: "Personalized Asset Allocation",
    description:
      "Get a tailored mix across stocks, mutual funds, government bonds, fixed deposits, and gold — built around your specific risk band.",
  },
  {
    icon: LineChart,
    title: "Curated Stock & Sector Recommendations",
    description:
      "Explore the sectors and specific stocks matched to your profile, each with a short explanation of why it was recommended.",
  },
  {
    icon: LayoutDashboard,
    title: "Interactive Dashboard",
    description:
      "Your risk profile, portfolio allocation, and recommendations all live in one dashboard you can revisit any time.",
  },
];

const TECH_STACK = [
  {
    group: "Frontend",
    icon: Code2,
    items: ["React", "React Router", "CSS3"],
  },
  {
    group: "Backend",
    icon: Server,
    items: ["Python", "Flask / FastAPI", "REST API"],
  },
  {
    group: "Machine Learning",
    icon: Cpu,
    items: [
      "scikit-learn",
      "Random Forest",
      "SHAP",
      "LIME",
      "Pandas",
      "NumPy",
    ],
  },
];

const TEAM = [
  {
    name: "Komolika",
    role: "Frontend Developer",
    quote:
      "Hello, myself Komolika. I'm the frontend developer — I take care of everything you see and interact with here.",
    photo: null,
  },
  {
    name: "[Backend Developer Name]",
    role: "Backend Developer",
    quote:
      "Hello, I'm [Name]. I'm the backend developer — I build and maintain the APIs and server logic that power this platform.",
    photo: null,
  },
  {
    name: "[ML Engineer Name]",
    role: "ML Engineer",
    quote:
      "Hello, I'm [Name]. I'm the ML engineer — I design and train the models that predict your risk profile and explain every recommendation.",
    photo: null,
  },
];

function TeamPhoto({ member }) {
  if (member.photo) {
    return (
      <div className="team-photo">
        <img src={member.photo} alt={member.name} />
      </div>
    );
  }

  return (
    <div className="team-photo team-photo-placeholder">
      <User size={54} strokeWidth={1.4} />
    </div>
  );
}

function DashboardPreview() {
  return (
    <div className="dashboard-preview">
      <div className="preview-glow"></div>

      <div className="preview-card risk-card">
        <div className="preview-card-header">
          <span>Risk Profile</span>
          <ShieldCheck size={16} />
        </div>

        <div className="risk-content">
          <div className="gauge">
            <div className="gauge-needle"></div>
          </div>

          <div>
            <strong>Moderate</strong>
            <span>72% confidence</span>
          </div>
        </div>
      </div>

      <div className="preview-card allocation-card">
        <div className="preview-card-header">
          <span>Portfolio Allocation</span>
          <PieChart size={16} />
        </div>

        <div className="allocation-content">
          <div className="donut">
            <div className="donut-center">100%</div>
          </div>

          <div className="allocation-list">
            <div>
              <span className="dot stocks"></span>
              Stocks
              <strong>60%</strong>
            </div>

            <div>
              <span className="dot funds"></span>
              Mutual Funds
              <strong>25%</strong>
            </div>

            <div>
              <span className="dot bonds"></span>
              Bonds
              <strong>10%</strong>
            </div>

            <div>
              <span className="dot gold"></span>
              Gold
              <strong>5%</strong>
            </div>
          </div>
        </div>
      </div>

      <div className="preview-card recommendation-card">
        <div className="preview-card-header">
          <span>Top Recommendation</span>
          <LineChart size={16} />
        </div>

        <div className="recommendation-content">
          <div className="stock-icon">H</div>

          <div className="stock-info">
            <strong>HDFCBANK</strong>
            <span>Banking · Large Cap</span>
          </div>

          <div className="stock-growth">
            +2.45%
            <small>↗</small>
          </div>
        </div>

        <div className="chart-line">
          <span></span>
          <span></span>
          <span></span>
          <span></span>
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  );
}

function Features() {
  return (
    <div className="features-page">
      <Navbar />

      <main>
        {/* HERO */}
        <section className="features-hero">
          <div className="hero-background-circle circle-one"></div>
          <div className="hero-background-circle circle-two"></div>

          <div className="features-container hero-container">
            <div className="hero-content">
              <p className="features-tag">ABOUT THE PROJECT</p>

              <div className="title-line"></div>

              <h1>
                What is <span>PortfolioIQ?</span>
              </h1>

              <p className="hero-description">
                PortfolioIQ is an AI-powered personalized stock portfolio
                recommendation system built as an MCA major project. It
                combines a guided risk-profiling questionnaire with a machine
                learning model to classify your investment risk appetite, then
                uses that prediction to generate a tailored asset allocation
                and stock recommendations.
              </p>

              <p className="hero-description">
                Every prediction is paired with SHAP and LIME explainability,
                so instead of a black-box answer, you see exactly which factors
                shaped your result and why.
              </p>

              <div className="tech-stack">
                {TECH_STACK.map((stack) => {
                  const StackIcon = stack.icon;

                  return (
                    <div className="tech-group" key={stack.group}>
                      <div className="tech-heading">
                        <StackIcon size={14} />
                        <span>{stack.group}</span>
                      </div>

                      <div className="tech-items">
                        {stack.items.map((item) => (
                          <span className="tech-badge" key={item}>
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="hero-visual">
              <DashboardPreview />
            </div>
          </div>
        </section>

        {/* FEATURES */}
        <section className="features-section">
          <div className="features-container">
            <div className="section-heading">
              <p className="features-tag">WHAT YOU GET</p>

              <div className="title-line centered"></div>

              <h2>Features</h2>

              <p>
                Everything you need to understand your risk and build a
                smarter investment portfolio.
              </p>
            </div>

            <div className="features-grid">
              {FEATURES.map((feature) => {
                const Icon = feature.icon;

                return (
                  <div className="feature-card" key={feature.title}>
                    <div className="feature-icon">
                      <Icon size={27} strokeWidth={1.8} />
                    </div>

                    <h3>{feature.title}</h3>

                    <p>{feature.description}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* TEAM */}
        <section className="team-section">
          <div className="features-container">
            <div className="section-heading">
              <p className="features-tag">WHO BUILT THIS</p>

              <div className="title-line centered"></div>

              <h2>Meet the Team</h2>
            </div>

            <div className="team-list">
              {TEAM.map((member, index) => (
                <div
                  className={`team-row ${
                    index % 2 !== 0 ? "team-row-reverse" : ""
                  }`}
                  key={member.role}
                >
                  <TeamPhoto member={member} />

                  <div className="team-card">
                    <p className="team-quote">{member.quote}</p>

                    <p className="team-name">{member.name}</p>

                    <p className="team-role">{member.role}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="features-cta-section">
          <div className="cta-wave wave-one"></div>
          <div className="cta-wave wave-two"></div>

          <div className="cta-content">
            <p className="features-tag">START YOUR JOURNEY</p>

            <h2>
              Ready to see your
              <br />
              risk profile?
            </h2>

            <p>
              Discover your investment risk profile and get personalized
              recommendations.
            </p>

            <Link to="/signup" className="cta-button">
              Get Started
              <ArrowRight size={18} />
            </Link>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      {/* <footer className="new-footer">
        <div className="features-container footer-container">
          <div className="footer-brand">
            <h2>
              Portfolio<span>IQ</span>
            </h2>

            <p>
              AI-powered portfolio recommendations
              <br />
              with explainable machine learning.
            </p>
          </div>

          <div className="footer-column">
            <h4>Product</h4>

            <Link to="/dashboard/recommendations">
              Recommendations
            </Link>

            <Link to="/dashboard/risk-assessment">
              Risk Analysis
            </Link>

            <Link to="/dashboard">Dashboard</Link>
          </div>

          <div className="footer-column">
            <h4>Company</h4>

            <Link to="/features">About</Link>

            <Link to="/features">Contact</Link>

            <Link to="/features">Privacy</Link>
          </div>

          <div className="footer-column newsletter">
            <h4>Newsletter</h4>

            <p>
              Stay updated with the latest insights and features.
            </p>

            <div className="newsletter-form">
              <input
                type="email"
                placeholder="Enter your email"
              />

              <button type="button">
                <ArrowRight size={18} />
              </button>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          © 2026 PortfolioIQ. Academic Demo Project.
        </div>
      </footer> */}
      <Footer />
    </div>
  );
}

export default Features;
