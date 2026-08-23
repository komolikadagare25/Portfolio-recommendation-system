import React from "react";
import { useNavigate } from "react-router-dom";
import MarketPanel from "../components/MarketPanel";
import AuthForm from "../components/AuthForm";
import { useAuth } from "../context/AuthContext";
import "./AuthScreen.css";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = () => {
    login({ name: "Test User", email: "test@example.com" });
    navigate("/dashboard");
  };

  return (
    <div className="auth-screen">
      <div className="auth-screen__card">
        <MarketPanel />
        <AuthForm mode="login" onSubmit={handleSubmit} />

        {/* TEMPORARY — remove once AuthForm's real submit button is confirmed working */}
        <button
          onClick={handleSubmit}
          style={{
            position: "fixed",
            bottom: 20,
            right: 20,
            padding: "10px 16px",
            background: "#14b8a6",
            color: "#0a0e1a",
            border: "none",
            borderRadius: 8,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Skip to Dashboard (dev only)
        </button>
      </div>
    </div>
  );
}
