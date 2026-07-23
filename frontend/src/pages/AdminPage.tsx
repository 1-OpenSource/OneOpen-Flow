import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminService, type SsoAdminConfig } from "../services/api";

type Tab = "users" | "roles" | "sso" | "accounts";

export function AdminPage() {
  const [tab, setTab] = useState<Tab>("users");
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: () => import("../services/api").then((m) => m.authService.me()) });
  const canAdmin = me.data && (me.data.role === "owner" || me.data.role === "admin");

  if (me.isLoading) {
    return <div className="page"><p className="muted">Loading…</p></div>;
  }

  if (!canAdmin) {
    return (
      <div className="page">
        <div className="page-header">
          <div>
            <h1>Administration</h1>
            <p>Owner or admin role required for RBAC, SSO, and service accounts.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Administration</h1>
          <p>Manage users, roles, SSO, and service accounts for Agentic AI.</p>
        </div>
      </div>
      <div className="tabs">
        {([
          ["users", "Users & invites"],
          ["roles", "Roles & permissions"],
          ["sso", "SSO (OIDC)"],
          ["accounts", "Service accounts"],
        ] as const).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`tab ${tab === id ? "active" : ""}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === "users" && <UsersPanel qc={qc} />}
      {tab === "roles" && <RolesPanel />}
      {tab === "sso" && <SsoPanel />}
      {tab === "accounts" && <ServiceAccountsPanel qc={qc} />}
    </div>
  );
}

function UsersPanel({ qc }: { qc: ReturnType<typeof useQueryClient> }) {
  const { data: users = [] } = useQuery({ queryKey: ["admin-users"], queryFn: adminService.users });
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [inviteResult, setInviteResult] = useState("");

  const invite = useMutation({
    mutationFn: () => adminService.invite({ email, role }),
    onSuccess: (res) => {
      setInviteResult(res.accept_url);
      setEmail("");
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });

  return (
    <div className="grid-2">
      <form
        className="card stack"
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          invite.mutate();
        }}
      >
        <h3>Invite user</h3>
        <div className="form-field">
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="form-field">
          <label>Role</label>
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="admin">admin</option>
            <option value="member">member</option>
            <option value="viewer">viewer</option>
          </select>
        </div>
        <button className="btn btn-primary" type="submit">Send invite</button>
        {inviteResult && (
          <p className="muted">
            Invite link (share securely): <code>{inviteResult}</code>
          </p>
        )}
      </form>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Auth</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td>
                  <select
                    value={u.role}
                    onChange={async (e) => {
                      await adminService.updateUser(u.id, { role: e.target.value });
                      qc.invalidateQueries({ queryKey: ["admin-users"] });
                    }}
                  >
                    <option value="owner">owner</option>
                    <option value="admin">admin</option>
                    <option value="member">member</option>
                    <option value="viewer">viewer</option>
                  </select>
                </td>
                <td>{u.auth_provider}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={u.is_active}
                    onChange={async (e) => {
                      await adminService.updateUser(u.id, { is_active: e.target.checked });
                      qc.invalidateQueries({ queryKey: ["admin-users"] });
                    }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RolesPanel() {
  const { data } = useQuery({ queryKey: ["admin-permissions"], queryFn: adminService.permissions });
  if (!data) return <p className="muted">Loading permissions…</p>;
  return (
    <div className="card stack">
      <p className="muted">Role → permission matrix used by the API and UI.</p>
      <table className="table">
        <thead>
          <tr>
            <th>Role</th>
            <th>Permissions</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(data.roles).map(([role, perms]) => (
            <tr key={role}>
              <td><strong>{role}</strong></td>
              <td><code>{perms.join(", ")}</code></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SsoPanel() {
  const { data, refetch } = useQuery({ queryKey: ["admin-sso"], queryFn: adminService.getSso });
  const [form, setForm] = useState<Partial<SsoAdminConfig> & { oidc_client_secret?: string }>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) setForm({ ...data, oidc_client_secret: "" });
  }, [data]);

  if (!data) return <p className="muted">Loading SSO…</p>;

  return (
    <form
      className="card stack"
      onSubmit={async (e) => {
        e.preventDefault();
        const payload = { ...form };
        if (!payload.oidc_client_secret) delete payload.oidc_client_secret;
        await adminService.updateSso(payload);
        setSaved(true);
        refetch();
      }}
    >
      <h3>OpenID Connect</h3>
      <p className="muted">Configure your identity provider (Okta, Azure AD, Keycloak, Google, etc.).</p>
      <label className="row">
        <input
          type="checkbox"
          checked={!!form.sso_enabled}
          onChange={(e) => setForm((f) => ({ ...f, sso_enabled: e.target.checked }))}
        />
        Enable SSO
      </label>
      <label className="row">
        <input
          type="checkbox"
          checked={form.allow_local_login !== false}
          onChange={(e) => setForm((f) => ({ ...f, allow_local_login: e.target.checked }))}
        />
        Allow email/password login
      </label>
      <div className="form-field">
        <label>Provider name</label>
        <input
          value={form.sso_provider_name || ""}
          onChange={(e) => setForm((f) => ({ ...f, sso_provider_name: e.target.value }))}
        />
      </div>
      <div className="form-field">
        <label>Issuer URL</label>
        <input
          value={form.oidc_issuer || ""}
          onChange={(e) => setForm((f) => ({ ...f, oidc_issuer: e.target.value }))}
          placeholder="https://login.example.com/oauth2/default"
        />
      </div>
      <div className="form-field">
        <label>Client ID</label>
        <input
          value={form.oidc_client_id || ""}
          onChange={(e) => setForm((f) => ({ ...f, oidc_client_id: e.target.value }))}
        />
      </div>
      <div className="form-field">
        <label>Client secret {data.oidc_client_secret_set ? "(set — leave blank to keep)" : ""}</label>
        <input
          type="password"
          value={form.oidc_client_secret || ""}
          onChange={(e) => setForm((f) => ({ ...f, oidc_client_secret: e.target.value }))}
          placeholder="••••••••"
        />
      </div>
      <div className="form-field">
        <label>Redirect URI</label>
        <input
          value={form.oidc_redirect_uri || ""}
          onChange={(e) => setForm((f) => ({ ...f, oidc_redirect_uri: e.target.value }))}
          placeholder="http://localhost:8000/api/auth/sso/callback"
        />
      </div>
      <div className="form-field">
        <label>Scopes</label>
        <input
          value={form.oidc_scopes || ""}
          onChange={(e) => setForm((f) => ({ ...f, oidc_scopes: e.target.value }))}
        />
      </div>
      <div className="form-field">
        <label>Default role for new SSO users</label>
        <select
          value={form.oidc_default_role || "member"}
          onChange={(e) => setForm((f) => ({ ...f, oidc_default_role: e.target.value }))}
        >
          <option value="admin">admin</option>
          <option value="member">member</option>
          <option value="viewer">viewer</option>
        </select>
      </div>
      <button className="btn btn-primary" type="submit">Save SSO settings</button>
      {saved && <p className="muted">Saved.</p>}
    </form>
  );
}

function ServiceAccountsPanel({ qc }: { qc: ReturnType<typeof useQueryClient> }) {
  const { data: keys = [] } = useQuery({ queryKey: ["admin-service-accounts"], queryFn: adminService.serviceAccounts });
  const [name, setName] = useState("AI Orchestrator");
  const [clientId, setClientId] = useState("svc-ai-orchestrator");
  const [createdToken, setCreatedToken] = useState("");

  return (
    <div className="grid-2">
      <form
        className="card stack"
        onSubmit={async (e) => {
          e.preventDefault();
          const res = await adminService.createServiceAccount({
            name,
            client_id: clientId || undefined,
            description: "Agentic AI service account",
            scopes: ["workflows:read", "workflows:run", "exposed:invoke"],
          });
          setCreatedToken(res.client_secret || res.token);
          setName("");
          setClientId("");
          qc.invalidateQueries({ queryKey: ["admin-service-accounts"] });
        }}
      >
        <h3>Create service account</h3>
        <p className="muted">
          For Agentic AI and CI. The client secret is shown once — store it in your agent vault.
        </p>
        <div className="form-field">
          <label>Display name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="form-field">
          <label>Client ID</label>
          <input
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            placeholder="svc-ai-orchestrator"
          />
        </div>
        <button className="btn btn-primary" type="submit">Create service account</button>
        {createdToken && (
          <p className="muted">
            Client secret (copy now): <code>{createdToken}</code>
          </p>
        )}
      </form>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Client ID</th>
              <th>Scopes</th>
              <th>Active</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k.id}>
                <td>{k.name}</td>
                <td><code>{k.client_id || k.prefix}</code></td>
                <td>{(k.scopes || []).join(", ")}</td>
                <td>{k.is_active ? "yes" : "no"}</td>
                <td>
                  {k.is_active && (
                    <button
                      className="btn btn-danger"
                      type="button"
                      onClick={async () => {
                        await adminService.revokeServiceAccount(k.id);
                        qc.invalidateQueries({ queryKey: ["admin-service-accounts"] });
                      }}
                    >
                      Revoke
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!keys.length && (
              <tr><td colSpan={5} className="muted">No service accounts yet. Create one for your AI agent.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
