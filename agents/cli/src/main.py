"""OneOpen CLI execution agent."""

from __future__ import annotations

import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

API_BASE = os.getenv("FLOW_API_URL", "http://localhost:8000")
AGENT_ID = os.getenv("AGENT_ID")
AGENT_TOKEN = os.getenv("AGENT_TOKEN")


def register() -> tuple[str, str]:
    if AGENT_ID and AGENT_TOKEN:
        return AGENT_ID, AGENT_TOKEN
    response = httpx.post(
        f"{API_BASE}/api/agents/register",
        json={
            "name": os.getenv("AGENT_NAME", "cli-agent-local"),
            "agent_type": "cli",
            "operating_system": platform.system().lower(),
            "supported_shells": ["bash", "powershell", "cmd", "python", "node"],
            "tags": ["cli", platform.system().lower(), "powershell" if os.name == "nt" else "bash"],
            "capabilities": ["bash", "powershell", "cmd", "artifacts"],
            "version": "0.1.0",
            "profile": os.getenv("AGENT_PROFILE", "restricted"),
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data["id"], data["token"]


def heartbeat(agent_id: str, token: str, workload: int) -> None:
    httpx.post(
        f"{API_BASE}/api/agents/heartbeat",
        headers={"X-Agent-Id": agent_id, "X-Agent-Token": token},
        json={"status": "busy" if workload else "idle", "current_workload": workload},
        timeout=15,
    )


def claim(agent_id: str, token: str) -> dict | None:
    response = httpx.post(
        f"{API_BASE}/api/agents/{agent_id}/claim-job",
        headers={"X-Agent-Token": token},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("job")


def complete(agent_id: str, token: str, job_id: str, status: str, result: dict, logs: list[str]) -> None:
    httpx.post(
        f"{API_BASE}/api/agents/{agent_id}/complete-job",
        params={"job_id": job_id},
        headers={"X-Agent-Token": token},
        json={"status": status, "result": result, "logs": logs},
        timeout=60,
    )


def mask(text: str, secrets: dict[str, str]) -> str:
    masked = text
    for value in secrets.values():
        if value:
            masked = masked.replace(value, "***")
    return masked


def execute(job: dict) -> tuple[str, dict, list[str]]:
    payload = job.get("payload", {}).get("payload", job.get("payload", {}))
    config = payload.get("config") or {}
    secrets = payload.get("secrets") or {}
    shell = str(config.get("shell", "powershell" if os.name == "nt" else "bash")).lower()
    command = config.get("command") or ""
    timeout = float(config.get("timeoutSeconds", 600))
    allowed = set(config.get("allowedExitCodes") or [0])
    workspace = Path(tempfile.mkdtemp(prefix="oneopen-cli-"))
    cwd = config.get("workingDirectory") or str(workspace)
    Path(cwd).mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in (config.get("environment") or {}).items()})
    env.update(secrets)

    if shell == "bash":
        cmd = ["bash", "-lc", command]
    elif shell in {"powershell", "pwsh"}:
        exe = "pwsh" if shell == "pwsh" else "powershell"
        cmd = [exe, "-NoProfile", "-NonInteractive", "-Command", command]
    elif shell == "cmd":
        cmd = ["cmd", "/c", command]
    elif shell == "python":
        script = workspace / "script.py"
        script.write_text(str(config.get("script") or command), encoding="utf-8")
        cmd = ["python", str(script)]
    else:
        cmd = [str(config.get("executable") or command)]

    try:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return (
            "failed",
            {
                "status": "failed",
                "failure_classification": "command_timeout",
                "error": f"Timed out after {timeout}s",
                "exitCode": -1,
            },
            ["timeout"],
        )

    stdout = mask(completed.stdout or "", secrets)
    stderr = mask(completed.stderr or "", secrets)
    passed = completed.returncode in allowed
    result = {
        "status": "passed" if passed else "failed",
        "exitCode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "outputs": {"exitCode": completed.returncode},
        "failure_classification": None if passed else "cli_non_zero_exit_code",
        "error": None if passed else f"Exit code {completed.returncode}",
    }
    logs = stdout.splitlines()[-100:]
    # scrub workspace secrets by deleting temp dir
    try:
        for path in workspace.rglob("*"):
            if path.is_file():
                path.unlink(missing_ok=True)
        workspace.rmdir()
    except OSError:
        pass
    return result["status"], result, logs


def main() -> None:
    agent_id, token = register()
    print(f"CLI agent registered: {agent_id}")
    workload = 0
    last_beat = 0.0
    while True:
        now = time.time()
        if now - last_beat > 5:
            heartbeat(agent_id, token, workload)
            last_beat = now
        job = claim(agent_id, token)
        if not job:
            time.sleep(2)
            continue
        workload += 1
        status, result, logs = execute(job)
        complete(agent_id, token, job["id"], status, result, logs)
        workload = max(0, workload - 1)


if __name__ == "__main__":
    main()
