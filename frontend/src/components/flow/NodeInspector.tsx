import Editor from "@monaco-editor/react";
import type { Node } from "@xyflow/react";

type Props = {
  selected?: Node;
  onRename: (name: string) => void;
  onUpdateConfig: (config: Record<string, unknown>) => void;
};

export function NodeInspector({ selected, onRename, onUpdateConfig }: Props) {
  if (!selected) {
    return (
      <aside className="inspector">
        <div className="inspector-header">Configuration</div>
        <div className="page muted">Select a node to configure it.</div>
      </aside>
    );
  }

  const config = (selected.data.config as Record<string, unknown>) || {};
  const configJson = JSON.stringify(config, null, 2);

  return (
    <aside className="inspector">
      <div className="inspector-header">
        <span>Configuration</span>
        <span className="badge">{String(selected.data.nodeType)}</span>
      </div>
      <div className="page stack">
        <div className="form-field">
          <label>Node name</label>
          <input
            value={String(selected.data.label || "")}
            onChange={(e) => onRename(e.target.value)}
          />
        </div>
        <div className="form-field">
          <label>Type</label>
          <input value={String(selected.data.nodeType || "")} disabled />
        </div>
        <div className="form-field">
          <label>Config (JSON)</label>
          <div style={{ border: "1px solid var(--border)", borderRadius: 10, overflow: "hidden" }}>
            <Editor
              height="280px"
              defaultLanguage="json"
              value={configJson}
              theme="vs-dark"
              onChange={(value) => {
                try {
                  onUpdateConfig(JSON.parse(value || "{}"));
                } catch {
                  // keep editing until valid
                }
              }}
              options={{ minimap: { enabled: false }, fontSize: 12 }}
            />
          </div>
        </div>
        {Object.entries(config).slice(0, 8).map(([key, value]) => (
          <div className="form-field" key={key}>
            <label>{key}</label>
            <input
              value={typeof value === "string" || typeof value === "number" ? String(value) : JSON.stringify(value)}
              onChange={(e) => {
                onUpdateConfig({ ...config, [key]: e.target.value });
              }}
            />
          </div>
        ))}
      </div>
    </aside>
  );
}
