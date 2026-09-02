import React, { useEffect, useMemo, useState } from "react";
import { Menu } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import "./Topbar.css";

// Pools of greetings, grouped by how the portfolio is actually doing, so the
// line under the user's name doesn't read the same on every single visit.
const GREETINGS = {
  up: [
    "your portfolio is looking healthy today.",
    "things are trending up for your portfolio today.",
    "your holdings are having a good day.",
    "green across the board for your portfolio today.",
  ],
  down: [
    "your portfolio is down a little today — nothing your long-term plan hasn't seen before.",
    "a few red numbers today. Short-term dips happen, don't panic.",
    "your portfolio dipped slightly today.",
  ],
  flat: [
    "your portfolio is holding steady today.",
    "a quiet day for your portfolio — no big moves.",
    "your portfolio is roughly flat today.",
  ],
};

function timeOfDayGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

/**
 * @param {{ onToggleNav?: () => void, navOpen?: boolean, portfolioTrend?: "up" | "down" | "flat" }} props
 */
export default function Topbar({ onToggleNav, navOpen, portfolioTrend = "flat" }) {
  const { user } = useAuth();
  const firstName = user?.name?.split(" ")[0] || "there";

  // Pick a message deterministically per day+trend so it stays put for the
  // whole session/day instead of flickering on every re-render, but still
  // varies day to day and with how the portfolio is actually performing.
  const message = useMemo(() => {
    const pool = GREETINGS[portfolioTrend] || GREETINGS.flat;
    const dayIndex = new Date().getDate();
    return pool[dayIndex % pool.length];
  }, [portfolioTrend]);

  const [displayedMessage, setDisplayedMessage] = useState(message);
  const [fading, setFading] = useState(false);

  useEffect(() => {
    if (message === displayedMessage) return;
    setFading(true);
    const t = setTimeout(() => {
      setDisplayedMessage(message);
      setFading(false);
    }, 180);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message]);

  const toneClass =
    portfolioTrend === "up" ? "dsb-topbar__greeting--up"
      : portfolioTrend === "down" ? "dsb-topbar__greeting--down"
      : "";

  return (
    <header className="dsb-topbar">
      <button
        type="button"
        className="dsb-topbar__nav-toggle"
        onClick={onToggleNav}
        aria-label={navOpen ? "Close menu" : "Open menu"}
        aria-expanded={!!navOpen}
      >
        <Menu size={20} strokeWidth={2} />
      </button>

      <p
        className={`dsb-topbar__greeting ${toneClass} ${fading ? "dsb-topbar__greeting--fading" : ""}`}
        aria-live="polite"
      >
        {timeOfDayGreeting()}, <strong>{firstName}</strong> — {displayedMessage}
      </p>

      <div className="dsb-topbar__actions">
        <div className="dsb-topbar__avatar">{firstName.charAt(0)}</div>
      </div>
    </header>
  );
}
