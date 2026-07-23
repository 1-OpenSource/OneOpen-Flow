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

export type UserAccount = {
  id: string;
  name: string;
  email: string;
  role: string;
  auth_provider: string;
  is_active: boolean;
  created_at: string;
};

export type RolePermissions = {
  roles: Record<string, string[]>;
  permissions: string[];
};

export type SsoAdminConfig = {
  sso_enabled: boolean;
  sso_provider_name: string;
  oidc_issuer?: string | null;
  oidc_client_id?: string | null;
  oidc_client_secret_set: boolean;
  oidc_redirect_uri?: string | null;
  oidc_scopes: string;
  oidc_default_role: string;
  allow_local_login: boolean;
};

export type ApiKeyMeta = {
  id: string;
  name: string;
  client_id?: string;
  description?: string | null;
  prefix: string;
  scopes: string[];
  is_active: boolean;
  expires_at?: string | null;
  last_used_at?: string | null;
  created_at: string;
};

export type ExposedWorkflow = {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  input_schema: Record<string, unknown>;
  tags: string[];
  current_version: number;
};

export const authService = {
  setupStatus: async () => (await apiClient.get("/api/auth/setup-status")).data as { needs_owner: boolean },
  register: async (payload: { name: string; email: string; password: string }) =>
    (await apiClient.post("/api/auth/register", payload)).data,
  login: async (payload: { email: string; password: string }) =>
    (await apiClient.post("/api/auth/login", payload)).data as { access_token: string },
  me: async () => (await apiClient.get("/api/auth/me")).data as UserAccount,
  ssoConfig: async () =>
    (await apiClient.get("/api/auth/sso/config")).data as {
      enabled: boolean;
      provider_name: string;
      authorize_url?: string | null;
      allow_local_login: boolean;
    },
  acceptInvite: async (payload: { token: string; name: string; password: string }) =>
    (await apiClient.post("/api/auth/accept-invite", payload)).data as { access_token: string },
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
  expose: async (
    id: string,
    payload: { enabled: boolean; slug?: string; description?: string; input_schema?: Record<string, unknown> },
  ) => (await apiClient.put(`/api/workflows/${id}/expose`, payload)).data as WorkflowDetail,
};

export const exposedService = {
  list: async () => (await apiClient.get("/api/exposed/workflows")).data as ExposedWorkflow[],
  get: async (slug: string) => (await apiClient.get(`/api/exposed/workflows/${slug}`)).data,
  invoke: async (slug: string, inputs: Record<string, unknown> = {}) =>
    (await apiClient.post(`/api/exposed/workflows/${slug}/invoke`, { inputs })).data as {
      id: string;
      status: string;
    },
};

export const agenticService = {
  catalog: async () => (await apiClient.get("/api/agentic/catalog")).data,
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
  update: async (id: string, payload: Partial<{ is_enabled: boolean; tags: string[]; max_workload: number }>) =>
    (await apiClient.patch(`/api/agents/${id}`, payload)).data as Agent,
  revoke: async (id: string) => apiClient.delete(`/api/agents/${id}`),
};

export const secretService = {
  list: async () => (await apiClient.get("/api/secrets")).data as SecretMeta[],
  create: async (payload: { name: string; value: string; description?: string }) =>
    (await apiClient.post("/api/secrets", payload)).data as SecretMeta,
  update: async (id: string, payload: { value?: string; description?: string }) =>
    (await apiClient.put(`/api/secrets/${id}`, payload)).data as SecretMeta,
  remove: async (id: string) => apiClient.delete(`/api/secrets/${id}`),
};

export const environmentService = {
  list: async () => (await apiClient.get("/api/environments")).data as Environment[],
  create: async (payload: { name: string; description?: string; variables: Record<string, unknown> }) =>
    (await apiClient.post("/api/environments", payload)).data as Environment,
  update: async (
    id: string,
    payload: Partial<{ name: string; description: string; variables: Record<string, unknown> }>,
  ) => (await apiClient.put(`/api/environments/${id}`, payload)).data as Environment,
  remove: async (id: string) => apiClient.delete(`/api/environments/${id}`),
};

export const adminService = {
  users: async () => (await apiClient.get("/api/admin/users")).data as UserAccount[],
  updateUser: async (id: string, payload: Partial<{ role: string; is_active: boolean; name: string }>) =>
    (await apiClient.patch(`/api/admin/users/${id}`, payload)).data as UserAccount,
  permissions: async () => (await apiClient.get("/api/admin/permissions")).data as RolePermissions,
  invite: async (payload: { email: string; role: string }) =>
    (await apiClient.post("/api/admin/invites", payload)).data as {
      invite: { id: string; email: string; role: string };
      accept_token: string;
      accept_url: string;
    },
  getSso: async () => (await apiClient.get("/api/admin/sso")).data as SsoAdminConfig,
  updateSso: async (payload: Partial<SsoAdminConfig> & { oidc_client_secret?: string }) =>
    (await apiClient.put("/api/admin/sso", payload)).data as SsoAdminConfig,
  apiKeys: async () => (await apiClient.get("/api/admin/api-keys")).data as ApiKeyMeta[],
  createApiKey: async (payload: {
    name: string;
    client_id?: string;
    description?: string;
    scopes?: string[];
    expires_in_days?: number;
  }) =>
    (await apiClient.post("/api/admin/api-keys", payload)).data as {
      key: ApiKeyMeta;
      token: string;
      client_secret?: string;
    },
  revokeApiKey: async (id: string) => apiClient.delete(`/api/admin/api-keys/${id}`),
  serviceAccounts: async () =>
    (await apiClient.get("/api/admin/service-accounts")).data as ApiKeyMeta[],
  createServiceAccount: async (payload: {
    name: string;
    client_id?: string;
    description?: string;
    scopes?: string[];
    expires_in_days?: number;
  }) =>
    (await apiClient.post("/api/admin/service-accounts", payload)).data as {
      key: ApiKeyMeta;
      token: string;
      service_account?: ApiKeyMeta;
      client_secret?: string;
    },
  revokeServiceAccount: async (id: string) => apiClient.delete(`/api/admin/service-accounts/${id}`),
};
