import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ClipboardList,
  Briefcase,
  Sparkles,
  History,
  Settings,
  HelpCircle,
  TrendingUp,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import "./Sidebar.css";

const NAV_ITEMS = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard, end: true },
  { label: "Risk Assessment", to: "/dashboard/risk-assessment", icon: ClipboardList },
  { label: "My Portfolio", to: "/dashboard/portfolio", icon: Briefcase },
  { label: "Recommendations", to: "/dashboard/recommendations", icon: Sparkles },
  { label: "History", to: "/dashboard/history", icon: History },
];

const FOOTER_ITEMS = [
  { label: "Settings", to: "/dashboard/settings", icon: Settings },
  { label: "Help", to: "/dashboard/help", icon: HelpCircle },
];

export default function Sidebar() {
  const { user } = useAuth();

  return (
    <aside className="dsb-sidebar">
      <div className="dsb-sidebar__brand">
        <span className="dsb-sidebar__logo-mark">
          <TrendingUp size={16} strokeWidth={2.25} color="#fff" />
        </span>
        Portfolio<span className="dsb-sidebar__brand-accent">IQ</span>
      </div>

      <nav className="dsb-sidebar__nav">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `dsb-sidebar__link ${isActive ? "dsb-sidebar__link--active" : ""}`}
          >
            <item.icon size={17} strokeWidth={1.75} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="dsb-sidebar__footer-nav">
        {FOOTER_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `dsb-sidebar__link ${isActive ? "dsb-sidebar__link--active" : ""}`}
          >
            <item.icon size={17} strokeWidth={1.75} />
            {item.label}
          </NavLink>
        ))}
      </div>

      <div className="dsb-sidebar__user">
        <div className="dsb-sidebar__avatar">{(user?.name || "U").charAt(0)}</div>
        <div>
          <p className="dsb-sidebar__user-name">{user?.name || "User"}</p>
          <p className="dsb-sidebar__user-role">Retail Investor</p>
        </div>
      </div>
    </aside>
  );
}
