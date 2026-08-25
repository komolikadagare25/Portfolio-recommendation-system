import { Link } from "react-router-dom";
import "./Navbar.css";

function Navbar() {
  return (
    <nav className="navbar">

      <div className="nav-logo">
        Portfolio<span>IQ</span>
      </div>

      <div className="nav-links">

        <Link to="/">
          Home
        </Link>

        <Link to="/features">
          Features
        </Link>

        <Link to="/design">
          System Design
        </Link>

        <Link to="/login">
          Login
        </Link>

        <Link
          to="/signup"
          className="nav-btn"
        >
          Get Started
        </Link>

      </div>

    </nav>
  );
}

export default Navbar;