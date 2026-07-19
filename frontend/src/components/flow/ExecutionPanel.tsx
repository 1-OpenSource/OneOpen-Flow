import { useMemo } from "react";

type LogEvent = {
  type: string;
  nodeId?: string;
  name?: string;
  status?: string;
  message?: string;
  error?: string;
  durationMs?: number;
};

type Props = {
  events: LogEvent[];
  currentNode?: string | null;
  status?: string;
  startedAt?: string | null;
  durationMs?: number | null;
};

export function ExecutionPanel({ events, currentNode, status, startedAt, durationMs }: Props) {
  const text = useMemo(
    () =>
      events
        .map((e) => {
          const parts = [e.type, e.nodeId || e.name, e.status, e.error || e.message, e.durationMs != null ? `${e.durationMs}ms` : ""]
            .filter(Boolean)
            .join(" · ");
          return parts;
        })
        .join("\n"),
    [events],
  );

  return (
    <section className="bottom-panel">
      <div className="bottom-header">
        <span>Live execution</span>
        <div className="row">
          <span className={`badge ${status || "idle"}`}>{status || "idle"}</span>
          <span className="muted">Current: {currentNode || "—"}</span>
          <span className="muted">Start: {startedAt ? new Date(startedAt).toLocaleTimeString() : "—"}</span>
          <span className="muted">Duration: {durationMs != null ? `${durationMs}ms` : "—"}</span>
        </div>
      </div>
      <div className="log-stream">{text || "Run a workflow to stream live logs here."}</div>
    </section>
  );
}
