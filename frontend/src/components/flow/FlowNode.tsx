import { Handle, Position, type NodeProps } from "@xyflow/react";

type FlowNodeData = {
  label: string;
  nodeType: string;
  category: string;
  status?: string;
  durationMs?: number;
  outputCount?: number;
  retryStatus?: string;
  error?: string;
};

export function FlowNode({ data, selected }: NodeProps) {
  const d = data as FlowNodeData;
  return (
    <div className={`flow-node ${d.category} ${d.status === "running" ? "running" : ""} ${selected ? "selected" : ""}`}>
      <Handle type="target" position={Position.Left} />
      <div className="head">
        <div>
          <strong>{d.label}</strong>
          <div className="muted" style={{ fontSize: "0.75rem" }}>{d.nodeType}</div>
        </div>
        <span className={`badge ${d.status || "idle"}`}>{d.status || "idle"}</span>
      </div>
      <div className="meta">
        <span>{d.durationMs != null ? `${d.durationMs}ms` : "—"}</span>
        <span>{d.outputCount ?? 0} outs</span>
        <span>{d.retryStatus || ""}</span>
        {d.error ? <span className="error-text">!</span> : null}
      </div>
      {d.nodeType === "if_else" ? (
        <>
          <Handle type="source" id="true" position={Position.Right} style={{ top: "35%" }} />
          <Handle type="source" id="false" position={Position.Right} style={{ top: "70%" }} />
        </>
      ) : (
        <Handle type="source" position={Position.Right} />
      )}
    </div>
  );
}
