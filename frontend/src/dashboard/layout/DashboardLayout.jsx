import React, { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import "./DashboardLayout.css";

/**
 * Wraps every /dashboard/* route. The matched child page renders via <Outlet />.
 */
export default function DashboardLayout() {
  const [navOpen, setNavOpen] = useState(false);
  const location = useLocation();

  // Close the mobile drawer automatically whenever the route changes.
  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  return (
    <div className={`dsb-shell ${navOpen ? "dsb-shell--nav-open" : ""}`}>
      <Sidebar onNavigate={() => setNavOpen(false)} />
      <div
        className="dsb-sidebar__scrim"
        onClick={() => setNavOpen(false)}
        aria-hidden={!navOpen}
      />

      <div className="dsb-main">
        <Topbar onToggleNav={() => setNavOpen((v) => !v)} navOpen={navOpen} />

        <div className="dsb-main__content">
          {/* key forces a remount on route change, which re-triggers the
              fade/rise-in animation so every page feels alive, not static. */}
          <div className="dsb-page-transition" key={location.pathname}>
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  );
}
