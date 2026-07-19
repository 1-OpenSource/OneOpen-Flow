import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authService } from "../services/api";
import { setAuthToken } from "../utils/storage";

export function LoginPage() {
  const navigate = useNavigate();
  const [needsOwner, setNeedsOwner] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    authService.setupStatus().then((s) => {
      setNeedsOwner(s.needs_owner);
      if (s.needs_owner) setMode("register");
    });
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      if (mode === "register") {
        await authService.register({ name, email, password });
      }
      const token = await authService.login({ email, password });
      setAuthToken(token.access_token);
      navigate("/workflows");
    } catch {
      setError("Authentication failed");
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={onSubmit}>
        <div className="auth-brand">
          <img src="/logos/oneopen-flow.svg" width={48} height={48} alt="OneOpen Flow" />
          <div>
            <h1>OneOpen Flow</h1>
            <p>Workflow orchestration</p>
          </div>
        </div>
        <p>{needsOwner ? "Create the first owner account." : "Sign in to design and run workflows."}</p>
        {mode === "register" && (
          <div className="form-field">
            <label htmlFor="name">Name</label>
            <input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              autoComplete="name"
              required
            />
          </div>
        )}
        <div className="form-field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            autoComplete="email"
            required
          />
        </div>
        <div className="form-field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            required
          />
        </div>
        {error && <div className="error-text">{error}</div>}
        <div className="form-actions">
          <button className="btn btn-primary" type="submit">
            {mode === "register" ? "Create account" : "Sign in"}
          </button>
          {!needsOwner && (
            <button className="btn" type="button" onClick={() => setMode(mode === "login" ? "register" : "login")}>
              {mode === "login" ? "Register" : "Back to login"}
            </button>
          )}
        </div>
        <p className="muted" style={{ marginTop: 16 }}>
          Part of the OneOpenSource platform. <Link to="/workflows">Continue</Link>
        </p>
      </form>
    </div>
  );
}
