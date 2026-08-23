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

        <a href="#features">
          Features
        </a>

        <a href="#about">
          About
        </a>

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