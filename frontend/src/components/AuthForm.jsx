import React, { useState } from "react";
import { Mail, Lock, User, Eye, EyeOff, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

const RISK_LEVELS = ["Low", "Medium", "High"];

export default function AuthForm({ mode = "login", onSubmit }) {
  const [showPassword, setShowPassword] = useState(false);
  const [risk, setRisk] = useState("Medium");
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: ""
  });
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const updateField = (field) => (e) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitting(true);

    Promise.resolve(onSubmit?.({ mode, ...form, risk })).finally(() => {
      setSubmitting(false);
      setDone(true);

      setTimeout(() => setDone(false), 1800);
    });
  };

  return (
    <div className="auth-form-panel">

      <div className="auth-form-panel__inner">

        <h1 className="auth-form-panel__title">
          {mode === "login"
            ? "Welcome back"
            : "Create your account"}
        </h1>


        <p className="auth-form-panel__subtitle">

          {mode === "login"
            ? "Log in to view your recommendations and portfolio."
            : "Set up a profile so we can tailor recommendations to you."}

        </p>


        <form 
          onSubmit={handleSubmit} 
          className="auth-form" 
          noValidate
        >


          {mode === "signup" && (

            <div className="field">

              <User 
                size={16} 
                strokeWidth={1.75} 
                className="field__icon" 
              />

              <input
                required
                type="text"
                placeholder="Full name"
                value={form.name}
                onChange={updateField("name")}
                className="field__input"
              />

            </div>

          )}



          <div className="field">

            <Mail 
              size={16} 
              strokeWidth={1.75} 
              className="field__icon" 
            />

            <input
              required
              type="email"
              placeholder="Email address"
              value={form.email}
              onChange={updateField("email")}
              className="field__input"
            />

          </div>



          <div className="field">

            <Lock 
              size={16} 
              strokeWidth={1.75} 
              className="field__icon" 
            />

            <input
              required
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              value={form.password}
              onChange={updateField("password")}
              className="field__input field__input--with-toggle"
            />


            <button
              type="button"
              className="field__toggle"
              onClick={() => setShowPassword((s) => !s)}
              tabIndex={-1}
            >

              {showPassword 
                ? <EyeOff size={16}/> 
                : <Eye size={16}/>
              }

            </button>


          </div>



          {mode === "signup" && (

            <div className="risk-select">

              <label className="risk-select__label">
                STARTING RISK PROFILE
              </label>


              <div className="risk-select__options">

                {RISK_LEVELS.map((r)=>(

                  <button
                    key={r}
                    type="button"
                    onClick={() => setRisk(r)}
                    className={`risk-select__option ${
                      risk === r 
                      ? "risk-select__option--active" 
                      : ""
                    }`}
                  >
                    {r}
                  </button>

                ))}


              </div>


              <p className="risk-select__hint">
                You can refine this anytime from your dashboard.
              </p>


            </div>

          )}




          {mode === "login" && (

            <div className="auth-form__forgot">

              <button 
                type="button" 
                className="link-btn"
              >
                Forgot password?
              </button>

            </div>

          )}




          <button 
            type="submit" 
            disabled={submitting}
            className="submit-btn"
          >

            {submitting ? (

              <span className="submit-btn__spinner"/>

            ) : done ? (

              "Success"

            ) : (

              <>
                {mode === "login" 
                  ? "Log in" 
                  : "Create account"
                }

                <ArrowRight size={16}/>

              </>

            )}

          </button>



        </form>



        <p className="auth-form-panel__switch">

          {mode === "login" ? (

            <>
              New to PortfolioIQ?{" "}

              <Link 
                to="/signup" 
                className="link-btn link-btn--strong"
              >
                Sign up
              </Link>
            </>


          ) : (

            <>
              Already have an account?{" "}

              <Link 
                to="/login" 
                className="link-btn link-btn--strong"
              >
                Log in
              </Link>
            </>

          )}


        </p>


      </div>

    </div>
  );
}