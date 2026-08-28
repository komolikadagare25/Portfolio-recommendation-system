import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import "./Footer.css";

function Footer() {
  return (
    <footer className="new-footer">
      <div className="features-container footer-container">

        {/* Brand */}
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

        {/* Product */}
        <div className="footer-column">
          <h4>Product</h4>

          <Link to="/dashboard/recommendations">
            Recommendations
          </Link>

          <Link to="/dashboard/risk-assessment">
            Risk Analysis
          </Link>

          <Link to="/dashboard">
            Dashboard
          </Link>
        </div>

        {/* Company */}
        <div className="footer-column">
          <h4>Company</h4>

          <Link to="/features">
            About
          </Link>

          <Link to="/features">
            Contact
          </Link>

          <Link to="/features">
            Privacy
          </Link>
        </div>

        {/* Newsletter */}
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

            <button type="button" aria-label="Subscribe">
              <ArrowRight size={18} />
            </button>
          </div>
        </div>

      </div>

      <div className="footer-bottom">
        © 2026 PortfolioIQ. Academic Demo Project.
      </div>
    </footer>
  );
}

export default Footer;