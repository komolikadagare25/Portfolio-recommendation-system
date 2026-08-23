import React from "react";
import { useAuth } from "../../context/AuthContext";
import "./Topbar.css";

export default function Topbar() {
  const { user } = useAuth();
  const firstName = user?.name?.split(" ")[0] || "there";

  return (
    <header className="dsb-topbar">
      <p className="dsb-topbar__greeting">
        Good morning, <strong>{firstName}</strong> — your portfolio is looking healthy today.
      </p>
      <div className="dsb-topbar__actions">
        <div className="dsb-topbar__avatar">{firstName.charAt(0)}</div>
      </div>
    </header>
  );
}
