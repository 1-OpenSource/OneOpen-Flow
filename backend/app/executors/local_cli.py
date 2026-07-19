from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.core.security import mask_secrets
from app.storage.service import StorageService


SHELL_MAP = {
    "bash": ["bash", "-lc"],
    "powershell": ["powershell", "-NoProfile", "-NonInteractive", "-Command"],
    "pwsh": ["pwsh", "-NoProfile", "-NonInteractive", "-Command"],
    "cmd": ["cmd", "/c"],
    "python": ["python"],
    "node": ["node"],
}


def execute_local_cli(
    *,
    config: dict[str, Any],
    secrets: dict[str, str],
    storage: StorageService,
    run_id: UUID,
) -> dict[str, Any]:
    settings = get_settings()
    shell = str(config.get("shell", "powershell" if os.name == "nt" else "bash")).lower()
    command = config.get("command")
    if not command:
        return {
            "status": "failed",
            "failure_classification": "workflow_configuration_error",
            "error": "CLI command is required",
        }

    workspace = storage.create_workspace(run_id, config.get("nodeId", "cli"))
    working_directory = config.get("workingDirectory") or str(workspace)
    Path(working_directory).mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    for key, value in (config.get("environment") or {}).items():
        env[str(key)] = str(value)
    for key, value in secrets.items():
        env[key] = value

    timeout = float(config.get("timeoutSeconds", 600))
    allowed = set(config.get("allowedExitCodes") or [0])
    args = list(config.get("arguments") or [])

    if shell in {"python", "node"} and config.get("script"):
        script_path = Path(workspace) / ("script.py" if shell == "python" else "script.js")
        script_path.write_text(str(config["script"]), encoding="utf-8")
        cmd = [*SHELL_MAP[shell], str(script_path), *args]
    elif shell == "run_custom_executable" or config.get("executable"):
        executable = config.get("executable")
        cmd = [executable, *args]
    else:
        launcher = SHELL_MAP.get(shell)
        if not launcher:
            return {
                "status": "failed",
                "failure_classification": "workflow_configuration_error",
                "error": f"Unsupported shell: {shell}",
            }
        full_command = command if not args else f"{command} {' '.join(str(a) for a in args)}"
        cmd = [*launcher, full_command]

    try:
        completed = subprocess.run(
            cmd,
            cwd=working_directory,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        storage.cleanup_workspace(Path(workspace))
        return {
            "status": "failed",
            "failure_classification": "command_timeout",
            "error": f"Command timed out after {timeout}s",
            "exitCode": -1,
        }
    except FileNotFoundError as exc:
        storage.cleanup_workspace(Path(workspace))
        return {
            "status": "failed",
            "failure_classification": "infrastructure_error",
            "error": str(exc),
            "exitCode": -1,
        }

    secret_values = list(secrets.values())
    stdout = mask_secrets(completed.stdout or "", secret_values)[: settings.max_cli_output_bytes]
    stderr = mask_secrets(completed.stderr or "", secret_values)[: settings.max_cli_output_bytes]
    exit_code = completed.returncode
    passed = exit_code in allowed

    artifacts = []
    for artifact_path in config.get("artifactPaths") or []:
        path = Path(working_directory) / artifact_path
        if path.exists():
            rel = f"artifacts/{run_id}/cli/{path.name}"
            stored = storage.save_bytes(relative_path=rel, data=path.read_bytes())
            artifacts.append({"name": path.name, "path": stored, "type": "file"})

    if config.get("captureStdout", True):
        rel = f"artifacts/{run_id}/cli/stdout.log"
        stored = storage.save_text(relative_path=rel, text=stdout)
        artifacts.append({"name": "stdout.log", "path": stored, "type": "stdout"})
    if config.get("captureStderr", True) and stderr:
        rel = f"artifacts/{run_id}/cli/stderr.log"
        stored = storage.save_text(relative_path=rel, text=stderr)
        artifacts.append({"name": "stderr.log", "path": stored, "type": "stderr"})

    outputs: dict[str, Any] = {"exitCode": exit_code}
    parsing = config.get("outputParsing") or {}
    if parsing.get("type") == "regex" and parsing.get("pattern"):
        import re

        match = re.search(parsing["pattern"], stdout)
        if match:
            outputs[parsing.get("outputKey", "parsed")] = match.group(1) if match.groups() else match.group(0)

    # Best-effort cleanup of env secret material from temp files
    storage.cleanup_workspace(Path(workspace))

    return {
        "status": "passed" if passed else "failed",
        "exitCode": exit_code,
        "stdout": stdout if config.get("captureStdout", True) else "",
        "stderr": stderr if config.get("captureStderr", True) else "",
        "outputs": outputs,
        "artifacts": artifacts,
        "logs": [line for line in stdout.splitlines()[-100:]],
        "failure_classification": None if passed else "cli_non_zero_exit_code",
        "error": None if passed else f"Exit code {exit_code} not in {sorted(allowed)}",
    }
