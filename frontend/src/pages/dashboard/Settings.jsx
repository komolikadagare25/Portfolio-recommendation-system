import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { RefreshCcw, ShieldAlert, CheckCircle2, AlertTriangle } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import "./Settings.css";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";

const NOTIF_KEY = "portfolioiq_notification_prefs";
const DEFAULT_PREFS = {
  weeklyDigest: true,
  riskChangeAlerts: true,
  productUpdates: false,
};

function loadPrefs() {
  try {
    const raw = localStorage.getItem(NOTIF_KEY);
    return raw ? { ...DEFAULT_PREFS, ...JSON.parse(raw) } : DEFAULT_PREFS;
  } catch {
    return DEFAULT_PREFS;
  }
}

export default function Settings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const token = localStorage.getItem("access_token");

  // ---- Profile ----
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileStatus, setProfileStatus] = useState(null); // { type: "success"|"error", message }

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setProfileSaving(true);
    setProfileStatus(null);
    try {
      const res = await fetch(`${API_BASE_URL}/me`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name, email }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Failed (${res.status})`);
      }
      setProfileStatus({ type: "success", message: "Profile updated." });
    } catch (err) {
      setProfileStatus({ type: "error", message: err.message });
    } finally {
      setProfileSaving(false);
    }
  };

  // ---- Notification preferences (stored locally on this device) ----
  const [prefs, setPrefs] = useState(loadPrefs);

  const togglePref = (key) => {
    const next = { ...prefs, [key]: !prefs[key] };
    setPrefs(next);
    localStorage.setItem(NOTIF_KEY, JSON.stringify(next));
  };

  // ---- Change password ----
  const [pwCurrent, setPwCurrent] = useState("");
  const [pwNew, setPwNew] = useState("");
  const [pwSaving, setPwSaving] = useState(false);
  const [pwStatus, setPwStatus] = useState(null);

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPwStatus(null);
    if (pwNew.length < 8) {
      setPwStatus({ type: "error", message: "New password must be at least 8 characters." });
      return;
    }
    setPwSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/change-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ current_password: pwCurrent, new_password: pwNew }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Failed (${res.status})`);
      }
      setPwStatus({ type: "success", message: "Password changed." });
      setPwCurrent("");
      setPwNew("");
    } catch (err) {
      setPwStatus({ type: "error", message: err.message });
    } finally {
      setPwSaving(false);
    }
  };

  // ---- Delete account ----
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteTyped, setDeleteTyped] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  const handleDeleteAccount = async () => {
    setDeleting(true);
    setDeleteError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/me`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      localStorage.removeItem("access_token");
      logout();
      navigate("/");
    } catch (err) {
      setDeleteError(err.message);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="settings-page">
      <div className="settings-page__header">
        <h1>Settings</h1>
        <p>Manage your profile, notifications, and account security.</p>
      </div>

      {/* Profile */}
      <section className="settings-panel">
        <h2 className="settings-panel__title">Profile</h2>
        <form className="settings-form" onSubmit={handleSaveProfile}>
          <div className="settings-form__row">
            <label htmlFor="settings-name">Full name</label>
            <input id="settings-name" type="text" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="settings-form__row">
            <label htmlFor="settings-email">Email</label>
            <input id="settings-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>

          {profileStatus && (
            <p className={`settings-status settings-status--${profileStatus.type}`}>
              {profileStatus.type === "success" ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
              {profileStatus.message}
            </p>
          )}

          <button type="submit" className="settings-btn settings-btn--primary" disabled={profileSaving}>
            {profileSaving ? "Saving…" : "Save changes"}
          </button>
        </form>
      </section>

      {/* Retake risk assessment */}
      <section className="settings-panel settings-panel--row">
        <div>
          <h2 className="settings-panel__title">Risk profile</h2>
          <p className="settings-panel__subtext">
            Circumstances change — retake the questionnaire any time to refresh your risk band and recommendations.
          </p>
        </div>
        <Link to="/dashboard/risk-assessment" className="settings-btn settings-btn--secondary">
          <RefreshCcw size={15} strokeWidth={2} />
          Retake Risk Assessment
        </Link>
      </section>

      {/* Notification preferences */}
      <section className="settings-panel">
        <h2 className="settings-panel__title">Notifications</h2>
        <p className="settings-panel__subtext">Stored locally on this device.</p>

        <div className="settings-toggle-list">
          <ToggleRow
            label="Weekly portfolio digest"
            description="A summary of how your recommended allocation is doing, once a week."
            checked={prefs.weeklyDigest}
            onChange={() => togglePref("weeklyDigest")}
          />
          <ToggleRow
            label="Risk band change alerts"
            description="Notify me if a new assessment moves me into a different risk band."
            checked={prefs.riskChangeAlerts}
            onChange={() => togglePref("riskChangeAlerts")}
          />
          <ToggleRow
            label="Product updates"
            description="Occasional emails about new PortfolioIQ features."
            checked={prefs.productUpdates}
            onChange={() => togglePref("productUpdates")}
          />
        </div>
      </section>

      {/* Security */}
      <section className="settings-panel">
        <h2 className="settings-panel__title">Change password</h2>
        <form className="settings-form" onSubmit={handleChangePassword}>
          <div className="settings-form__row">
            <label htmlFor="settings-pw-current">Current password</label>
            <input id="settings-pw-current" type="password" value={pwCurrent} onChange={(e) => setPwCurrent(e.target.value)} required />
          </div>
          <div className="settings-form__row">
            <label htmlFor="settings-pw-new">New password</label>
            <input id="settings-pw-new" type="password" value={pwNew} onChange={(e) => setPwNew(e.target.value)} required />
          </div>

          {pwStatus && (
            <p className={`settings-status settings-status--${pwStatus.type}`}>
              {pwStatus.type === "success" ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
              {pwStatus.message}
            </p>
          )}

          <button type="submit" className="settings-btn settings-btn--primary" disabled={pwSaving}>
            {pwSaving ? "Updating…" : "Update password"}
          </button>
        </form>
      </section>

      {/* Danger zone */}
      <section className="settings-panel settings-panel--danger">
        <h2 className="settings-panel__title settings-panel__title--danger">
          <ShieldAlert size={16} strokeWidth={2} />
          Danger zone
        </h2>
        <p className="settings-panel__subtext">
          Deleting your account permanently removes your profile, reports, and history. This can't be undone.
        </p>

        {!deleteConfirmOpen ? (
          <button className="settings-btn settings-btn--danger" onClick={() => setDeleteConfirmOpen(true)}>
            Delete account
          </button>
        ) : (
          <div className="settings-delete-confirm">
            <p>Type <strong>DELETE</strong> to confirm.</p>
            <input
              type="text"
              value={deleteTyped}
              onChange={(e) => setDeleteTyped(e.target.value)}
              placeholder="DELETE"
            />
            {deleteError && <p className="settings-status settings-status--error"><AlertTriangle size={14} />{deleteError}</p>}
            <div className="settings-delete-confirm__actions">
              <button
                className="settings-btn settings-btn--danger"
                disabled={deleteTyped !== "DELETE" || deleting}
                onClick={handleDeleteAccount}
              >
                {deleting ? "Deleting…" : "Permanently delete"}
              </button>
              <button
                className="settings-btn settings-btn--secondary"
                onClick={() => { setDeleteConfirmOpen(false); setDeleteTyped(""); setDeleteError(null); }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function ToggleRow({ label, description, checked, onChange }) {
  return (
    <div className="settings-toggle-row">
      <div>
        <p className="settings-toggle-row__label">{label}</p>
        <p className="settings-toggle-row__description">{description}</p>
      </div>
      <button
        role="switch"
        aria-checked={checked}
        onClick={onChange}
        className={`settings-switch ${checked ? "settings-switch--on" : ""}`}
      >
        <span className="settings-switch__knob" />
      </button>
    </div>
  );
}
