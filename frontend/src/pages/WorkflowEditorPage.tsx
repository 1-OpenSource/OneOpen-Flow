import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Node,
  type OnSelectionChangeParams,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { FlowNode } from "../components/flow/FlowNode";
import { NodePalette } from "../components/flow/NodePalette";
import { NodeInspector } from "../components/flow/NodeInspector";
import { ExecutionPanel } from "../components/flow/ExecutionPanel";
import {
  categoryFor,
  definitionToFlow,
  flowToDefinition,
  useStudioStore,
} from "../stores/studioStore";
import { workflowService } from "../services/api";

const nodeTypes = { flowNode: FlowNode };

export function WorkflowEditorPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = !id || id === "new";

  const name = useStudioStore((s) => s.name);
  const description = useStudioStore((s) => s.description);
  const variables = useStudioStore((s) => s.variables);
  const workflowId = useStudioStore((s) => s.workflowId);
  const selectedNodeId = useStudioStore((s) => s.selectedNodeId);
  const validationErrors = useStudioStore((s) => s.validationErrors);
  const setMeta = useStudioStore((s) => s.setMeta);
  const selectNode = useStudioStore((s) => s.selectNode);
  const loadDefinitionMeta = useStudioStore((s) => s.loadDefinitionMeta);
  const setValidationErrors = useStudioStore((s) => s.setValidationErrors);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [events] = useState<Array<Record<string, unknown>>>([]);
  const [runStatus, setRunStatus] = useState<string>("idle");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let cancelled = false;

    if (isNew) {
      const startId = `node-${crypto.randomUUID().slice(0, 8)}`;
      const endId = `node-${crypto.randomUUID().slice(0, 8)}`;
      const initialNodes: Node[] = [
        {
          id: startId,
          type: "flowNode",
          position: { x: 80, y: 120 },
          data: { label: "Start", nodeType: "start", category: "logic", config: {} },
        },
        {
          id: endId,
          type: "flowNode",
          position: { x: 420, y: 120 },
          data: { label: "End", nodeType: "end", category: "logic", config: {} },
        },
      ];
      const initialEdges = [{ id: `edge-${crypto.randomUUID().slice(0, 8)}`, source: startId, target: endId }];
      setNodes(initialNodes);
      setEdges(initialEdges);
      setMeta("Untitled workflow", "");
      selectNode(undefined);
      return;
    }

    workflowService.get(id!).then((wf) => {
      if (cancelled) return;
      loadDefinitionMeta(wf.id, wf.definition);
      const graph = definitionToFlow(wf.definition);
      setNodes(graph.nodes);
      setEdges(graph.edges);
    });

    return () => {
      cancelled = true;
    };
  }, [id, isNew, loadDefinitionMeta, selectNode, setEdges, setMeta, setNodes]);

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges],
  );

  const onSelectionChange = useCallback(
    ({ nodes: selected }: OnSelectionChangeParams) => {
      selectNode(selected[0]?.id);
    },
    [selectNode],
  );

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId),
    [nodes, selectedNodeId],
  );

  const updateSelectedConfig = useCallback(
    (config: Record<string, unknown>) => {
      if (!selectedNodeId) return;
      setNodes((ns) =>
        ns.map((n) => (n.id === selectedNodeId ? { ...n, data: { ...n.data, config } } : n)),
      );
    },
    [selectedNodeId, setNodes],
  );

  const renameSelected = useCallback(
    (label: string) => {
      if (!selectedNodeId) return;
      setNodes((ns) =>
        ns.map((n) => (n.id === selectedNodeId ? { ...n, data: { ...n.data, label } } : n)),
      );
    },
    [selectedNodeId, setNodes],
  );

  const addNode = (type: string, name: string, defaults?: Record<string, unknown>) => {
    const newNode: Node = {
      id: `node-${crypto.randomUUID().slice(0, 8)}`,
      type: "flowNode",
      position: { x: 180 + nodes.length * 24, y: 80 + nodes.length * 36 },
      data: {
        label: name,
        nodeType: type,
        category: categoryFor(type),
        config: defaults || {},
        status: "idle",
      },
    };
    setNodes((ns) => [...ns, newNode]);
  };

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const raw = event.dataTransfer.getData("application/oneopen-node");
      if (!raw) return;
      const item = JSON.parse(raw) as { type: string; name: string; defaults?: Record<string, unknown> };
      const bounds = (event.target as HTMLElement).closest(".canvas-wrap")?.getBoundingClientRect();
      const position = {
        x: event.clientX - (bounds?.left || 0) - 80,
        y: event.clientY - (bounds?.top || 0) - 20,
      };
      setNodes((ns) => [
        ...ns,
        {
          id: `node-${crypto.randomUUID().slice(0, 8)}`,
          type: "flowNode",
          position,
          data: {
            label: item.name,
            nodeType: item.type,
            category: categoryFor(item.type),
            config: item.defaults || {},
            status: "idle",
          },
        },
      ]);
    },
    [setNodes],
  );

  async function save() {
    setSaving(true);
    setMessage("");
    try {
      const definition = flowToDefinition(
        { id: workflowId, name, description, variables },
        nodes,
        edges,
      );
      if (isNew) {
        const created = await workflowService.create({
          name: name || definition.name,
          description,
          definition,
        });
        setMessage("Saved");
        navigate(`/workflows/${created.id}/edit`, { replace: true });
      } else {
        await workflowService.update(id!, {
          name,
          description,
          definition,
        });
        setMessage("Saved");
      }
    } catch {
      setMessage("Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function validate() {
    if (isNew) {
      await save();
      return;
    }
    const result = await workflowService.validate(id!);
    setValidationErrors(result.issues.map((i) => `${i.severity}: ${i.message}`));
    setMessage(result.valid ? "Workflow is valid" : "Validation found issues");
  }

  async function run() {
    if (isNew) {
      setMessage("Save the workflow before running");
      return;
    }
    await save();
    const started = await workflowService.run(id!);
    setRunStatus(started.status);
    navigate(`/runs/${started.id}`);
  }

  async function exportJson() {
    if (isNew) return;
    const data = await workflowService.export(id!);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${name || "workflow"}.json`;
    a.click();
  }

  async function importJson(file: File) {
    const text = await file.text();
    const definition = JSON.parse(text);
    const created = await workflowService.import(definition);
    navigate(`/workflows/${created.id}/edit`);
  }

  const fitViewOptions = useMemo(() => ({ padding: 0.2 }), []);

  return (
    <div>
      <div className="topbar" style={{ borderTop: "1px solid var(--border)" }}>
        <div className="row">
          <input
            style={{ minWidth: 240 }}
            value={name}
            onChange={(e) => setMeta(e.target.value, description)}
          />
          <input
            style={{ minWidth: 280 }}
            placeholder="Description"
            value={description}
            onChange={(e) => setMeta(name, e.target.value)}
          />
          {message && <span className="muted">{message}</span>}
        </div>
        <div className="row">
          <label className="btn">
            Import
            <input
              type="file"
              accept="application/json"
              hidden
              onChange={(e) => e.target.files?.[0] && importJson(e.target.files[0])}
            />
          </label>
          <button className="btn" onClick={exportJson} disabled={isNew}>Export</button>
          <button className="btn" onClick={validate}>Validate</button>
          <button className="btn" onClick={save} disabled={saving}>{saving ? "Saving…" : "Save"}</button>
          <button className="btn btn-primary" onClick={run}>Run</button>
        </div>
      </div>
      {!!validationErrors.length && (
        <div className="page" style={{ paddingBottom: 0 }}>
          <div className="card error-text">
            {validationErrors.map((err) => <div key={err}>{err}</div>)}
          </div>
        </div>
      )}
      <div className="studio">
        <NodePalette onAdd={addNode} />
        <div
          className="canvas-wrap"
          onDragOver={(e) => e.preventDefault()}
          onDrop={onDrop}
        >
          <div className="canvas-toolbar">
            <button
              className="btn"
              onClick={() => {
                if (!selectedNodeId) return;
                setNodes((ns) => ns.filter((n) => n.id !== selectedNodeId));
                selectNode(undefined);
              }}
            >
              Delete
            </button>
            <button
              className="btn"
              onClick={() => {
                if (!selectedNode) return;
                setNodes((ns) => [
                  ...ns,
                  {
                    ...selectedNode,
                    id: `node-${crypto.randomUUID().slice(0, 8)}`,
                    position: {
                      x: selectedNode.position.x + 40,
                      y: selectedNode.position.y + 40,
                    },
                    selected: false,
                  },
                ]);
              }}
            >
              Duplicate
            </button>
          </div>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={fitViewOptions}
            onSelectionChange={onSelectionChange}
          >
            <Background gap={18} />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>
        <NodeInspector
          selected={selectedNode}
          onRename={renameSelected}
          onUpdateConfig={updateSelectedConfig}
        />
        <ExecutionPanel events={events as never} status={runStatus} />
      </div>
    </div>
  );
}
