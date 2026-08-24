import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import MarketPanel from "../components/MarketPanel";
import AuthForm from "../components/AuthForm";
import { useAuth } from "../context/AuthContext";
import "./AuthScreen.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState(null);

  const handleSubmit = async ({ email, password }) => {
    setError(null);

    const res = await fetch(`${API_BASE_URL}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      setError("Invalid email or password");
      throw new Error("Login failed");
    }

    const { access_token } = await res.json();
    localStorage.setItem("access_token", access_token);

    const meRes = await fetch(`${API_BASE_URL}/me`, {
      headers: { Authorization: `Bearer ${access_token}` },
    });
    const me = await meRes.json();

    login({ name: me.name, email: me.email, token: access_token });
    navigate("/dashboard");
  };

  return (
    <div className="auth-screen">
      <div className="auth-screen__card">
        <MarketPanel />
        <AuthForm mode="login" onSubmit={handleSubmit} />
        {error && <p style={{ color: "red", textAlign: "center" }}>{error}</p>}
      </div>
    </div>
  );
}