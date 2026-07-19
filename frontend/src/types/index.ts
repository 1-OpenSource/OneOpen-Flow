export type WorkflowNodeDef = {
  id: string;
  type: string;
  name: string;
  config: Record<string, unknown>;
  position: { x: number; y: number };
};

export type WorkflowEdgeDef = {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string | null;
  targetHandle?: string | null;
  label?: string | null;
};

export type WorkflowDefinition = {
  id?: string;
  name: string;
  version: number;
  description?: string | null;
  variables: Record<string, unknown>;
  nodes: WorkflowNodeDef[];
  edges: WorkflowEdgeDef[];
  tags?: string[];
  trigger_type?: string;
};

export type WorkflowSummary = {
  id: string;
  name: string;
  description?: string | null;
  current_version: number;
  owner_id: string;
  tags: string[];
  trigger_type: string;
  last_run_at?: string | null;
  last_status?: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkflowDetail = WorkflowSummary & {
  definition: WorkflowDefinition;
};

export type NodeRun = {
  id: string;
  node_id: string;
  node_type: string;
  node_name: string;
  status: string;
  attempt: number;
  outputs: Record<string, unknown>;
  result: Record<string, unknown>;
  error?: string | null;
  failure_classification?: string | null;
  logs: string[];
  started_at?: string | null;
  ended_at?: string | null;
  duration_ms?: number | null;
};

export type Artifact = {
  id: string;
  name: string;
  artifact_type: string;
  storage_path: string;
  content_type?: string | null;
  size_bytes?: number | null;
  created_at: string;
};

export type WorkflowRun = {
  id: string;
  workflow_id: string;
  version: number;
  status: string;
  trigger_type: string;
  inputs: Record<string, unknown>;
  variables: Record<string, unknown>;
  failure_classification?: string | null;
  failure_message?: string | null;
  recommended_action?: string | null;
  current_node_id?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  duration_ms?: number | null;
  created_at: string;
  node_runs: NodeRun[];
  artifacts: Artifact[];
};

export type Agent = {
  id: string;
  name: string;
  agent_type: string;
  operating_system: string;
  supported_shells: string[];
  tags: string[];
  capabilities: string[];
  status: string;
  version: string;
  current_workload: number;
  max_workload: number;
  profile: string;
  last_heartbeat_at?: string | null;
  is_enabled: boolean;
  created_at: string;
};

export type SecretMeta = {
  id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
};

export type Environment = {
  id: string;
  name: string;
  description?: string | null;
  variables: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ValidationResult = {
  valid: boolean;
  issues: Array<{ severity: string; code: string; message: string; node_id?: string | null }>;
};
