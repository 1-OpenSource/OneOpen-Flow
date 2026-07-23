import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { authService } from "../services/api";
import { setAuthToken } from "../utils/storage";

export function LoginPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [needsOwner, setNeedsOwner] = useState(false);
  const [mode, setMode] = useState<"login" | "register" | "invite">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [sso, setSso] = useState<{ enabled: boolean; provider_name: string; authorize_url?: string | null; allow_local_login: boolean } | null>(null);
  const inviteToken = params.get("invite") || "";

  useEffect(() => {
    const ssoToken = params.get("sso_token");
    const ssoError = params.get("sso_error");
    if (ssoToken) {
      setAuthToken(ssoToken);
      navigate("/workflows");
      return;
    }
    if (ssoError) setError(`SSO failed: ${ssoError}`);
    if (inviteToken) setMode("invite");
    authService.setupStatus().then((s) => {
      setNeedsOwner(s.needs_owner);
      if (s.needs_owner) setMode("register");
    });
    authService.ssoConfig().then(setSso).catch(() => setSso(null));
  }, [navigate, params, inviteToken]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      if (mode === "invite") {
        const token = await authService.acceptInvite({ token: inviteToken, name, password });
        setAuthToken(token.access_token);
        navigate("/workflows");
        return;
      }
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

  const showLocal = !sso || sso.allow_local_login || needsOwner || mode === "invite";

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
        <p>
          {mode === "invite"
            ? "Accept your invite and set a password."
            : needsOwner
              ? "Create the first owner account."
              : "Sign in to design and run workflows."}
        </p>
        {sso?.enabled && sso.authorize_url && mode !== "invite" && (
          <a className="btn btn-primary" href={sso.authorize_url} style={{ textAlign: "center" }}>
            Continue with {sso.provider_name}
          </a>
        )}
        {showLocal && (
          <>
            {(mode === "register" || mode === "invite") && (
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
            {mode !== "invite" && (
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
            )}
            <div className="form-field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                required
              />
            </div>
            {error && <div className="error-text">{error}</div>}
            <div className="form-actions">
              <button className="btn btn-primary" type="submit">
                {mode === "invite" ? "Accept invite" : mode === "register" ? "Create account" : "Sign in"}
              </button>
              {!needsOwner && mode !== "invite" && (
                <button className="btn" type="button" onClick={() => setMode(mode === "login" ? "register" : "login")}>
                  {mode === "login" ? "Register" : "Back to login"}
                </button>
              )}
            </div>
          </>
        )}
        {!showLocal && error && <div className="error-text">{error}</div>}
        <p className="muted" style={{ marginTop: 16 }}>
          Part of the OneOpenSource platform. <Link to="/workflows">Continue</Link>
        </p>
      </form>
    </div>
  );
}
