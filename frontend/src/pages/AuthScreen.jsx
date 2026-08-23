import React from "react";
import MarketPanel from "../components/MarketPanel";
import AuthForm from "../components/AuthForm";
import "./AuthScreen.css";

/**
 * Login / signup screen for the AI-powered stock portfolio recommendation system.
 * Drop this in as a route, e.g. <Route path="/login" element={<AuthScreen />} />
 *
 * @param {{ onSubmit?: Function }} props - forwarded to AuthForm; called with
 *   { mode, name, email, password, risk } on submit. Wire this to your
 *   /api/auth/login and /api/auth/signup endpoints.
 */
export default function AuthScreen({ onSubmit }) {
  return (
    <div className="auth-screen">
      <div className="auth-screen__card">
        <MarketPanel />
        <AuthForm onSubmit={onSubmit} />
      </div>
    </div>
  );
}
