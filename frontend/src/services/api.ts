import { apiClient } from "./apiClient";
import type {
  Agent,
  Environment,
  SecretMeta,
  ValidationResult,
  WorkflowDefinition,
  WorkflowDetail,
  WorkflowRun,
  WorkflowSummary,
} from "../types";

export const authService = {
  setupStatus: async () => (await apiClient.get("/api/auth/setup-status")).data as { needs_owner: boolean },
  register: async (payload: { name: string; email: string; password: string }) =>
    (await apiClient.post("/api/auth/register", payload)).data,
  login: async (payload: { email: string; password: string }) =>
    (await apiClient.post("/api/auth/login", payload)).data as { access_token: string },
  me: async () => (await apiClient.get("/api/auth/me")).data,
};

export const workflowService = {
  list: async () => (await apiClient.get("/api/workflows")).data as WorkflowSummary[],
  get: async (id: string) => (await apiClient.get(`/api/workflows/${id}`)).data as WorkflowDetail,
  create: async (payload: { name: string; description?: string; definition?: WorkflowDefinition }) =>
    (await apiClient.post("/api/workflows", payload)).data as WorkflowDetail,
  update: async (id: string, payload: Partial<{ name: string; description: string; definition: WorkflowDefinition }>) =>
    (await apiClient.put(`/api/workflows/${id}`, payload)).data as WorkflowDetail,
  remove: async (id: string) => apiClient.delete(`/api/workflows/${id}`),
  validate: async (id: string) => (await apiClient.post(`/api/workflows/${id}/validate`)).data as ValidationResult,
  run: async (id: string, inputs: Record<string, unknown> = {}) =>
    (await apiClient.post(`/api/workflows/${id}/run`, { inputs })).data as { id: string; status: string },
  clone: async (id: string) => (await apiClient.post(`/api/workflows/${id}/clone`)).data as WorkflowDetail,
  export: async (id: string) => (await apiClient.get(`/api/workflows/${id}/export`)).data as WorkflowDefinition,
  import: async (definition: WorkflowDefinition) =>
    (await apiClient.post("/api/workflows/import", definition)).data as WorkflowDetail,
};

export const runService = {
  list: async (workflowId?: string) =>
    (await apiClient.get("/api/runs", { params: workflowId ? { workflow_id: workflowId } : {} })).data as WorkflowRun[],
  get: async (id: string) => (await apiClient.get(`/api/runs/${id}`)).data as WorkflowRun,
  cancel: async (id: string) => (await apiClient.post(`/api/runs/${id}/cancel`)).data as WorkflowRun,
  retry: async (id: string) => (await apiClient.post(`/api/runs/${id}/retry`)).data as { id: string; status: string },
  retryFromNode: async (id: string, nodeId: string) =>
    (await apiClient.post(`/api/runs/${id}/retry-from-node`, { node_id: nodeId })).data as { id: string; status: string },
  provideInput: async (id: string, payload: { otp?: string; value?: string; inputs?: Record<string, unknown> }) =>
    (await apiClient.post(`/api/runs/${id}/provide-input`, payload)).data as WorkflowRun,
  createWorkItem: async (id: string, payload: { project_id?: string; title?: string; additional_notes?: string }) =>
    (await apiClient.post(`/api/runs/${id}/create-work-item`, payload)).data,
  evidenceUrl: (id: string) => `${apiClient.defaults.baseURL}/api/runs/${id}/evidence`,
  eventsUrl: (id: string) => `${apiClient.defaults.baseURL}/api/runs/${id}/events`,
};

export const agentService = {
  list: async () => (await apiClient.get("/api/agents")).data as Agent[],
};

export const secretService = {
  list: async () => (await apiClient.get("/api/secrets")).data as SecretMeta[],
  create: async (payload: { name: string; value: string; description?: string }) =>
    (await apiClient.post("/api/secrets", payload)).data as SecretMeta,
  remove: async (id: string) => apiClient.delete(`/api/secrets/${id}`),
};

export const environmentService = {
  list: async () => (await apiClient.get("/api/environments")).data as Environment[],
  create: async (payload: { name: string; description?: string; variables: Record<string, unknown> }) =>
    (await apiClient.post("/api/environments", payload)).data as Environment,
};
