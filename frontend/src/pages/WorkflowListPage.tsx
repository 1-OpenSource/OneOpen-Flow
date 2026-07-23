import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Copy, Plus, Trash2 } from "lucide-react";
import { workflowService } from "../services/api";

export function WorkflowListPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { data = [], isLoading } = useQuery({
    queryKey: ["workflows"],
    queryFn: workflowService.list,
  });

  const clone = useMutation({
    mutationFn: (id: string) => workflowService.clone(id),
    onSuccess: (wf) => {
      qc.invalidateQueries({ queryKey: ["workflows"] });
      navigate(`/workflows/${wf.id}/edit`);
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => workflowService.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workflows"] }),
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
                <th>Exposed</th>
                <th>Last run</th>
                <th>Status</th>
                <th>Trigger</th>
                <th>Tags</th>
                <th />
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
                  <td>
                    {wf.is_exposed ? (
                      <span className="badge waiting" title={wf.expose_slug || ""}>
                        {wf.expose_slug}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td>{wf.last_run_at ? new Date(wf.last_run_at).toLocaleString() : "—"}</td>
                  <td><span className={`badge ${wf.last_status || ""}`}>{wf.last_status || "—"}</span></td>
                  <td>{wf.trigger_type}</td>
                  <td>{(wf.tags || []).join(", ") || "—"}</td>
                  <td>
                    <div className="row">
                      <button className="btn" type="button" title="Clone" onClick={() => clone.mutate(wf.id)}>
                        <Copy size={14} />
                      </button>
                      <button
                        className="btn btn-danger"
                        type="button"
                        title="Delete"
                        onClick={() => {
                          if (confirm(`Delete workflow "${wf.name}"?`)) remove.mutate(wf.id);
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!data.length && (
                <tr>
                  <td colSpan={9} className="muted">No workflows yet. Create one to get started.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
