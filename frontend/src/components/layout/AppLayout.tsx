import { NavLink, Outlet } from "react-router-dom";
import {
  Bot,
  FolderKey,
  GitBranch,
  LayoutDashboard,
  Settings,
  Moon,
  Sun,
} from "lucide-react";
import { getTheme, setTheme } from "../../utils/storage";
import { useState } from "react";

export function AppLayout() {
  const [theme, setThemeState] = useState(getTheme());

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <img
            className="brand-logo"
            src="/logos/oneopen-flow.svg"
            width={40}
            height={40}
            alt="OneOpen Flow"
          />
          <div className="brand-copy">
            <strong>OneOpen</strong>
            <span>Flow</span>
          </div>
        </div>
        <nav>
          <NavLink className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} to="/workflows">
            <GitBranch size={16} /> Workflows
          </NavLink>
          <NavLink className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} to="/agents">
            <Bot size={16} /> Agents
          </NavLink>
          <NavLink className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} to="/secrets">
            <FolderKey size={16} /> Secrets
          </NavLink>
          <NavLink className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} to="/environments">
            <LayoutDashboard size={16} /> Environments
          </NavLink>
          <NavLink className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`} to="/settings">
            <Settings size={16} /> Settings
          </NavLink>
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="muted">Visual workflows across browser, CLI, API, and database</div>
          <button
            className="btn"
            onClick={() => {
              const next = theme === "light" ? "dark" : "light";
              setTheme(next);
              setThemeState(next);
            }}
          >
            {theme === "light" ? <Moon size={14} /> : <Sun size={14} />}
            {theme === "light" ? "Dark" : "Light"} mode
          </button>
        </header>
        <Outlet />
      </div>
    </div>
  );
}
