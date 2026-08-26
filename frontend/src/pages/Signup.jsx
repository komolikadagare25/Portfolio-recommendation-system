import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import MarketPanel from "../components/MarketPanel";
import AuthForm from "../components/AuthForm";
import { useAuth } from "../context/AuthContext";
import "./AuthScreen.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

function Signup() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState(null);

  const handleSubmit = async ({ name, email, password }) => {
    setError(null);

    const res = await fetch(`${API_BASE_URL}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data.detail || "Registration failed");
      throw new Error("Registration failed");
    }

    const loginRes = await fetch(`${API_BASE_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const { access_token } = await loginRes.json();
    localStorage.setItem("access_token", access_token);

    login({ name, email, token: access_token });
    navigate("/dashboard");
  };

  return (
    <div className="auth-screen">
      <div className="auth-screen__card">
        <MarketPanel />
        <AuthForm mode="signup" onSubmit={handleSubmit} />
        {error && <p style={{ color: "red", textAlign: "center" }}>{error}</p>}
      </div>
    </div>
  );
}

export default Signup;