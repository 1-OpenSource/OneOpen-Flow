import { useQuery } from "@tanstack/react-query";
import { agentService } from "../services/api";

export function AgentsPage() {
  const { data = [] } = useQuery({ queryKey: ["agents"], queryFn: agentService.list });
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
                <td>{(agent.tags || []).join(", ")}</td>
                <td>{(agent.capabilities || []).join(", ")}</td>
                <td>{agent.current_workload}/{agent.max_workload}</td>
                <td>{agent.last_heartbeat_at ? new Date(agent.last_heartbeat_at).toLocaleString() : "—"}</td>
                <td>{agent.version}</td>
              </tr>
            ))}
            {!data.length && (
              <tr><td colSpan={9} className="muted">No agents registered. Local inline execution is used in development.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
