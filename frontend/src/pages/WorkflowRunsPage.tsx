import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { runService } from "../services/api";

export function WorkflowRunsPage() {
  const { id } = useParams();
  const { data = [] } = useQuery({
    queryKey: ["runs", id],
    queryFn: () => runService.list(id),
    enabled: !!id,
  });

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Workflow runs</h1>
          <p><Link to={`/workflows/${id}/edit`}>Back to editor</Link></p>
        </div>
      </div>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Status</th>
              <th>Trigger</th>
              <th>Started</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {data.map((run) => (
              <tr key={run.id}>
                <td><Link to={`/runs/${run.id}`}>{run.id.slice(0, 8)}</Link></td>
                <td><span className={`badge ${run.status}`}>{run.status}</span></td>
                <td>{run.trigger_type}</td>
                <td>{run.started_at ? new Date(run.started_at).toLocaleString() : "—"}</td>
                <td>{run.duration_ms != null ? `${run.duration_ms}ms` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
