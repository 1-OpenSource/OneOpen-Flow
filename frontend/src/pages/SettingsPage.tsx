import { clearAuthToken } from "../utils/storage";
import { Link, useNavigate } from "react-router-dom";

export function SettingsPage() {
  const navigate = useNavigate();
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Settings</h1>
          <p>Account controls and platform links.</p>
        </div>
      </div>
      <div className="card stack">
        <p className="muted">
          Administration (RBAC, SSO, service accounts) lives under{" "}
          <Link to="/admin">Admin</Link>. Agentic AI must use a{" "}
          <strong>service account</strong> token with{" "}
          <code>GET /api/agentic/catalog</code> and{" "}
          <code>/api/exposed/workflows/&#123;slug&#125;/invoke</code>.
        </p>
        <p className="muted">
          Workboard API integration uses <code>WORKBOARD_API_URL</code>. Locator healing default threshold is 90.
        </p>
        <button
          className="btn btn-danger"
          onClick={() => {
            clearAuthToken();
            navigate("/login");
          }}
        >
          Sign out
        </button>
      </div>
    </div>
  );
}
