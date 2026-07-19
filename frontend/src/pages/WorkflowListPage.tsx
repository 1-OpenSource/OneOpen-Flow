import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";
import { workflowService } from "../services/api";

export function WorkflowListPage() {
  const navigate = useNavigate();
  const { data = [], isLoading } = useQuery({
    queryKey: ["workflows"],
    queryFn: workflowService.list,
  });

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Workflows</h1>
          <p>Create visual workflows across browser, CLI, API, database, and validation steps.</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate("/workflows/new")}>
          <Plus size={16} /> New workflow
        </button>
      </div>
      <div className="card">
        {isLoading ? (
          <p className="muted">Loading workflows…</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Version</th>
                <th>Last run</th>
                <th>Status</th>
                <th>Trigger</th>
                <th>Tags</th>
              </tr>
            </thead>
            <tbody>
              {data.map((wf) => (
                <tr key={wf.id}>
                  <td>
                    <Link to={`/workflows/${wf.id}/edit`}><strong>{wf.name}</strong></Link>
                  </td>
                  <td className="muted">{wf.description || "—"}</td>
                  <td>v{wf.current_version}</td>
                  <td>{wf.last_run_at ? new Date(wf.last_run_at).toLocaleString() : "—"}</td>
                  <td><span className={`badge ${wf.last_status || ""}`}>{wf.last_status || "—"}</span></td>
                  <td>{wf.trigger_type}</td>
                  <td>{(wf.tags || []).join(", ") || "—"}</td>
                </tr>
              ))}
              {!data.length && (
                <tr>
                  <td colSpan={7} className="muted">No workflows yet. Create one to get started.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
