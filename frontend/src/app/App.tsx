import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";
import { ProtectedRoute } from "../components/layout/ProtectedRoute";
import { LoginPage } from "../pages/LoginPage";
import { WorkflowListPage } from "../pages/WorkflowListPage";
import { WorkflowEditorPage } from "../pages/WorkflowEditorPage";
import { WorkflowRunsPage } from "../pages/WorkflowRunsPage";
import { RunDetailsPage } from "../pages/RunDetailsPage";
import { AgentsPage } from "../pages/AgentsPage";
import { SecretsPage } from "../pages/SecretsPage";
import { EnvironmentsPage } from "../pages/EnvironmentsPage";
import { SettingsPage } from "../pages/SettingsPage";
import { AdminPage } from "../pages/AdminPage";
import { getTheme, setTheme } from "../utils/storage";

setTheme(getTheme());

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/workflows" replace />} />
          <Route path="/workflows" element={<WorkflowListPage />} />
          <Route path="/workflows/new" element={<WorkflowEditorPage />} />
          <Route path="/workflows/:id" element={<WorkflowEditorPage />} />
          <Route path="/workflows/:id/edit" element={<WorkflowEditorPage />} />
          <Route path="/workflows/:id/runs" element={<WorkflowRunsPage />} />
          <Route path="/runs/:runId" element={<RunDetailsPage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/secrets" element={<SecretsPage />} />
          <Route path="/environments" element={<EnvironmentsPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
