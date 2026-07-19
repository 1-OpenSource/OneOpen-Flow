import { clearAuthToken } from "../utils/storage";
import { useNavigate } from "react-router-dom";

export function SettingsPage() {
  const navigate = useNavigate();
  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Settings</h1>
          <p>OneOpen Flow module settings and account controls.</p>
        </div>
      </div>
      <div className="card stack">
        <p className="muted">
          Permissions follow the OneOpenSource model: view/edit/run workflows, manage agents and secrets,
          approve healed locators, and create Workboard defects.
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
