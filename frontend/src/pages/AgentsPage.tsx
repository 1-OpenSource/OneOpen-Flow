import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { agentService } from "../services/api";

export function AgentsPage() {
  const qc = useQueryClient();
  const { data = [] } = useQuery({ queryKey: ["agents"], queryFn: agentService.list });
  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      agentService.update(id, { is_enabled: enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agents"] }),
  });

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Agents</h1>
          <p>Registered browser and CLI execution agents.</p>
        </div>
      </div>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>OS</th>
              <th>Status</th>
              <th>Enabled</th>
              <th>Tags</th>
              <th>Capabilities</th>
              <th>Workload</th>
              <th>Heartbeat</th>
              <th>Version</th>
            </tr>
          </thead>
          <tbody>
            {data.map((agent) => (
              <tr key={agent.id}>
                <td>{agent.name}</td>
                <td>{agent.agent_type}</td>
                <td>{agent.operating_system}</td>
                <td><span className={`badge ${agent.status}`}>{agent.status}</span></td>
                <td>
                  <input
                    type="checkbox"
                    checked={agent.is_enabled}
                    onChange={(e) => toggle.mutate({ id: agent.id, enabled: e.target.checked })}
                  />
                </td>
                <td>{(agent.tags || []).join(", ")}</td>
                <td>{(agent.capabilities || []).join(", ")}</td>
                <td>{agent.current_workload}/{agent.max_workload}</td>
                <td>{agent.last_heartbeat_at ? new Date(agent.last_heartbeat_at).toLocaleString() : "—"}</td>
                <td>{agent.version}</td>
              </tr>
            ))}
            {!data.length && (
              <tr><td colSpan={10} className="muted">No agents registered. Local inline execution is used in development.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
