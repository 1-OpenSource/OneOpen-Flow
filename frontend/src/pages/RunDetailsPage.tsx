import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { runService } from "../services/api";
import { getAuthToken } from "../utils/storage";

export function RunDetailsPage() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [events, setEvents] = useState<Array<Record<string, unknown>>>([]);
  const [otp, setOtp] = useState("");
  const [submittingOtp, setSubmittingOtp] = useState(false);
  const [otpError, setOtpError] = useState("");
  const { data: run, refetch } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => runService.get(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && ["passed", "failed", "cancelled"].includes(status) ? false : 2000;
    },
  });

  useEffect(() => {
    if (!runId) return;
    const token = getAuthToken();
    const url = runService.eventsUrl(runId);
    const controller = new AbortController();
    (async () => {
      try {
        const response = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          signal: controller.signal,
        });
        if (!response.body) return;
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const chunks = buffer.split("\n\n");
          buffer = chunks.pop() || "";
          for (const chunk of chunks) {
            const line = chunk.split("\n").find((l) => l.startsWith("data: "));
            if (!line) continue;
            const payload = JSON.parse(line.slice(6));
            setEvents((prev) => [...prev, payload]);
            if (["run.completed", "run.failed", "run.cancelled", "run.waiting", "run.resumed"].includes(payload.type)) {
              refetch();
            }
          }
        }
      } catch {
        // ignore abort/network
      }
    })();
    return () => controller.abort();
  }, [runId, refetch]);

  if (!run) {
    return <div className="page muted">Loading run…</div>;
  }

  const failedNode = run.node_runs.find((n) => n.status === "failed");
  const waitingNode = run.node_runs.find((n) => n.status === "waiting" || n.status === "approval_required");
  const needsHumanInput = ["waiting", "approval_required"].includes(run.status) && !!waitingNode;

  async function submitOtp(e: FormEvent) {
    e.preventDefault();
    if (!otp.trim()) {
      setOtpError("Enter an OTP or verification code");
      return;
    }
    setSubmittingOtp(true);
    setOtpError("");
    try {
      await runService.provideInput(run!.id, { otp: otp.trim() });
      setOtp("");
      await refetch();
    } catch {
      setOtpError("Failed to submit OTP");
    } finally {
      setSubmittingOtp(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Run details</h1>
          <p>
            Workflow <Link to={`/workflows/${run.workflow_id}/edit`}>{run.workflow_id.slice(0, 8)}</Link> · v{run.version}
          </p>
        </div>
        <div className="row">
          <button className="btn" onClick={() => runService.cancel(run.id).then(() => refetch())}>Cancel</button>
          <button className="btn" onClick={() => runService.retry(run.id).then((r) => navigate(`/runs/${r.id}`))}>Retry</button>
          {failedNode && (
            <button
              className="btn"
              onClick={() =>
                runService.retryFromNode(run.id, failedNode.node_id).then((r) => navigate(`/runs/${r.id}`))
              }
            >
              Retry failed node
            </button>
          )}
          <a className="btn" href={runService.evidenceUrl(run.id)} target="_blank" rel="noreferrer">
            Download evidence
          </a>
          <button
            className="btn btn-danger"
            onClick={() =>
              runService.createWorkItem(run.id, { title: undefined }).then(() => alert("Workboard defect created"))
            }
          >
            Create defect
          </button>
        </div>
      </div>

      {needsHumanInput && (
        <form className="card stack" style={{ marginBottom: 16 }} onSubmit={submitOtp}>
          <div className="row">
            <span className={`badge ${run.status}`}>{run.status}</span>
            <strong>Human-in-the-loop</strong>
          </div>
          <p className="muted" style={{ margin: 0 }}>
            {(waitingNode?.outputs?.prompt as string) ||
              waitingNode?.node_name ||
              "Enter the OTP / verification code to continue this workflow."}
          </p>
          {(waitingNode?.outputs?.hint as string) && (
            <p className="muted" style={{ margin: 0 }}>{String(waitingNode.outputs.hint)}</p>
          )}
          <div className="form-field" style={{ marginBottom: 0, maxWidth: 360 }}>
            <label htmlFor="hitl-otp">OTP / verification code</label>
            <input
              id="hitl-otp"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              placeholder="123456"
              autoComplete="one-time-code"
              inputMode="numeric"
            />
          </div>
          {otpError && <div className="error-text">{otpError}</div>}
          <div className="form-actions">
            <button className="btn btn-primary" type="submit" disabled={submittingOtp}>
              {submittingOtp ? "Submitting…" : "Submit & resume"}
            </button>
          </div>
        </form>
      )}

      <div className="grid-2">
        <div className="card stack">
          <div className="row">
            <span className={`badge ${run.status}`}>{run.status}</span>
            <span className="muted">{run.duration_ms != null ? `${run.duration_ms}ms` : ""}</span>
          </div>
          {run.failure_classification && (
            <div>
              <strong>{run.failure_classification}</strong>
              <p className="muted">{run.failure_message}</p>
              <p>{run.recommended_action}</p>
            </div>
          )}
          <h3>Timeline</h3>
          {run.node_runs.map((nr) => (
            <div key={nr.id} className="card" style={{ boxShadow: "none" }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <div>
                  <strong>{nr.node_name}</strong>
                  <div className="muted">{nr.node_type}</div>
                </div>
                <span className={`badge ${nr.status}`}>{nr.status}</span>
              </div>
              <div className="muted">
                Attempt {nr.attempt} · {nr.duration_ms ?? 0}ms · outputs {Object.keys(nr.outputs || {}).length}
              </div>
              {nr.error && <div className="error-text">{nr.error}</div>}
              {!!(nr.result as { suggestions?: unknown })?.suggestions && (
                <pre className="log-stream">{JSON.stringify((nr.result as { suggestions?: unknown }).suggestions, null, 2)}</pre>
              )}
              {nr.result?.locator && (
                <div className="muted">
                  Locator confidence: {JSON.stringify(nr.result.locator)}
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="stack">
          <div className="card">
            <h3>Live logs</h3>
            <div className="log-stream">
              {events.map((e, idx) => (
                <div key={idx}>{JSON.stringify(e)}</div>
              ))}
              {!events.length && (run.node_runs.flatMap((n) => n.logs || []).join("\n") || "No logs yet")}
            </div>
          </div>
          <div className="card">
            <h3>Artifacts</h3>
            <ul>
              {run.artifacts.map((a) => (
                <li key={a.id}>{a.artifact_type}: {a.name}</li>
              ))}
              {!run.artifacts.length && <li className="muted">No artifacts</li>}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
