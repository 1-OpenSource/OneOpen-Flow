from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx

from app.executors.base import NodeExecutor, registry


class LogicExecutor(NodeExecutor):
    node_types = {
        "start",
        "end",
        "if_else",
        "loop",
        "for_each",
        "retry",
        "wait",
        "parallel_branch",
        "merge",
        "set_variable",
        "transform_variable",
        "call_sub_workflow",
        "stop_workflow",
    }

    def execute(self, *, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        node_type = context.get("node_type", "start")
        if node_type == "wait":
            seconds = float(config.get("seconds", 1))
            time.sleep(min(seconds, 300))
            return {"status": "passed", "outputs": {"waitedSeconds": seconds}}
        if node_type == "set_variable":
            key = config.get("key")
            value = config.get("value")
            return {"status": "passed", "outputs": {key: value} if key else {}}
        if node_type == "transform_variable":
            expression = config.get("expression", "")
            source = config.get("source")
            value = context.get("resolved", {}).get(source) if source else None
            if expression == "json_stringify":
                value = json.dumps(value)
            elif expression == "to_string":
                value = str(value)
            elif expression == "to_number":
                value = float(value) if value is not None else None
            return {"status": "passed", "outputs": {"value": value}}
        if node_type == "if_else":
            left = config.get("left")
            right = config.get("right")
            op = config.get("operator", "eq")
            result = _compare(left, right, op)
            return {
                "status": "passed",
                "outputs": {"branch": "true" if result else "false", "result": result},
            }
        if node_type == "stop_workflow":
            return {
                "status": "passed",
                "outputs": {"stopped": True, "reason": config.get("reason", "stopped")},
                "stop": True,
            }
        if node_type == "call_sub_workflow":
            return {
                "status": "passed",
                "outputs": {
                    "subWorkflowId": config.get("workflowId"),
                    "note": "Sub-workflow invocation recorded for Phase 1 orchestration",
                },
            }
        return {"status": "passed", "outputs": {}}


class ApiExecutor(NodeExecutor):
    node_types = {
        "rest_request",
        "assert_status_code",
        "assert_json_value",
        "extract_json_value",
        "validate_json_schema",
    }

    def execute(self, *, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        node_type = context.get("node_type", "rest_request")
        if node_type == "rest_request":
            return self._rest_request(config)
        previous = context.get("previous_result", {})
        response = previous.get("response") or context.get("api_response") or {}
        if node_type == "assert_status_code":
            expected = int(config.get("expected", 200))
            actual = int(response.get("statusCode", previous.get("statusCode", 0)))
            passed = actual == expected
            return {
                "status": "passed" if passed else "failed",
                "outputs": {"expected": expected, "actual": actual},
                "failure_classification": None if passed else "api_failure",
                "error": None if passed else f"Expected status {expected}, got {actual}",
            }
        if node_type == "extract_json_value":
            path = config.get("path", "")
            body = response.get("body") or previous.get("body")
            value = _json_path(body, path)
            output_key = config.get("outputKey", "value")
            return {"status": "passed", "outputs": {output_key: value}}
        if node_type == "assert_json_value":
            path = config.get("path", "")
            expected = config.get("expected")
            body = response.get("body") or previous.get("body")
            actual = _json_path(body, path)
            passed = actual == expected
            return {
                "status": "passed" if passed else "failed",
                "outputs": {"expected": expected, "actual": actual},
                "failure_classification": None if passed else "assertion_failure",
                "error": None if passed else f"JSON value mismatch at {path}",
            }
        if node_type == "validate_json_schema":
            try:
                from jsonschema import validate

                body = response.get("body") or previous.get("body")
                validate(instance=body, schema=config.get("schema", {}))
                return {"status": "passed", "outputs": {"valid": True}}
            except Exception as exc:  # noqa: BLE001
                return {
                    "status": "failed",
                    "outputs": {"valid": False},
                    "failure_classification": "assertion_failure",
                    "error": str(exc),
                }
        return {"status": "failed", "error": f"Unknown API node type {node_type}"}

    def _rest_request(self, config: dict[str, Any]) -> dict[str, Any]:
        method = str(config.get("method", "GET")).upper()
        url = config.get("url")
        if not url:
            return {
                "status": "failed",
                "failure_classification": "workflow_configuration_error",
                "error": "REST request requires url",
            }
        headers = dict(config.get("headers") or {})
        params = dict(config.get("query") or {})
        timeout = float(config.get("timeoutSeconds", 30))
        auth = config.get("authentication") or {}
        if auth.get("type") == "bearer" and auth.get("token"):
            headers["Authorization"] = f"Bearer {auth['token']}"
        elif auth.get("type") == "basic":
            # httpx handles tuple auth
            pass
        body = config.get("jsonBody")
        data = config.get("formData")
        retries = int(config.get("retry", 0))
        last_error = None
        for attempt in range(retries + 1):
            try:
                with httpx.Client(timeout=timeout) as client:
                    kwargs: dict[str, Any] = {"headers": headers, "params": params}
                    if auth.get("type") == "basic":
                        kwargs["auth"] = (auth.get("username", ""), auth.get("password", ""))
                    if body is not None:
                        kwargs["json"] = body
                    elif data is not None:
                        kwargs["data"] = data
                    response = client.request(method, url, **kwargs)
                    parsed: Any
                    try:
                        parsed = response.json()
                    except Exception:  # noqa: BLE001
                        parsed = response.text
                    return {
                        "status": "passed",
                        "statusCode": response.status_code,
                        "outputs": {
                            "statusCode": response.status_code,
                            "body": parsed,
                            "headers": dict(response.headers),
                        },
                        "response": {
                            "statusCode": response.status_code,
                            "body": parsed,
                            "headers": dict(response.headers),
                        },
                        "attempt": attempt + 1,
                    }
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                time.sleep(0.5 * (attempt + 1))
        return {
            "status": "failed",
            "failure_classification": "api_failure",
            "error": last_error or "REST request failed",
        }


class DatabaseExecutor(NodeExecutor):
    node_types = {
        "execute_query",
        "execute_command",
        "extract_scalar_value",
        "extract_rows",
        "assert_row_count",
        "assert_column_value",
    }

    def execute(self, *, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        from sqlalchemy import create_engine, text

        connection_url = config.get("connectionUrl") or context.get("secrets", {}).get(
            config.get("connectionSecret", "DATABASE_URL")
        )
        if not connection_url:
            return {
                "status": "failed",
                "failure_classification": "workflow_configuration_error",
                "error": "Database connection secret is required",
            }
        sql = config.get("sql") or config.get("query")
        if not sql:
            return {
                "status": "failed",
                "failure_classification": "workflow_configuration_error",
                "error": "SQL is required",
            }
        engine = create_engine(connection_url)
        node_type = context.get("node_type", "execute_query")
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql), config.get("params") or {})
                if node_type in {"execute_command"}:
                    conn.commit()
                    return {"status": "passed", "outputs": {"rowcount": result.rowcount}}
                rows = [dict(row._mapping) for row in result]
                if node_type == "extract_scalar_value":
                    value = None
                    if rows:
                        first = rows[0]
                        column = config.get("column") or next(iter(first.keys()))
                        value = first.get(column)
                    return {"status": "passed", "outputs": {"value": value, "rows": rows}}
                if node_type == "assert_row_count":
                    expected = int(config.get("expected", 0))
                    actual = len(rows)
                    passed = actual == expected
                    return {
                        "status": "passed" if passed else "failed",
                        "outputs": {"expected": expected, "actual": actual, "rows": rows},
                        "failure_classification": None if passed else "database_validation_failure",
                        "error": None if passed else f"Expected {expected} rows, got {actual}",
                    }
                if node_type == "assert_column_value":
                    column = config.get("column")
                    expected = config.get("expected")
                    actual = rows[0].get(column) if rows and column else None
                    passed = actual == expected
                    return {
                        "status": "passed" if passed else "failed",
                        "outputs": {"expected": expected, "actual": actual},
                        "failure_classification": None if passed else "database_validation_failure",
                        "error": None if passed else "Column value assertion failed",
                    }
                return {"status": "passed", "outputs": {"rows": rows, "rowCount": len(rows)}}
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "failed",
                "failure_classification": "database_validation_failure",
                "error": str(exc),
            }
        finally:
            engine.dispose()


class ValidationExecutor(NodeExecutor):
    node_types = {
        "compare_values",
        "regex_match",
        "json_assertion",
        "file_exists",
        "file_content_assertion",
        "exit_code_assertion",
        "numeric_threshold",
    }

    def execute(self, *, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        from pathlib import Path

        node_type = context.get("node_type", "compare_values")
        if node_type == "compare_values":
            left = config.get("left")
            right = config.get("right")
            op = config.get("operator", "eq")
            passed = _compare(left, right, op)
            return {
                "status": "passed" if passed else "failed",
                "outputs": {"left": left, "right": right, "operator": op},
                "failure_classification": None if passed else "assertion_failure",
                "error": None if passed else "Value comparison failed",
            }
        if node_type == "regex_match":
            pattern = config.get("pattern", "")
            text_value = str(config.get("text", ""))
            passed = re.search(pattern, text_value) is not None
            return {
                "status": "passed" if passed else "failed",
                "outputs": {"matched": passed},
                "failure_classification": None if passed else "assertion_failure",
                "error": None if passed else "Regex did not match",
            }
        if node_type == "file_exists":
            path = Path(str(config.get("path", "")))
            passed = path.exists()
            return {
                "status": "passed" if passed else "failed",
                "outputs": {"exists": passed, "path": str(path)},
                "failure_classification": None if passed else "file_missing",
                "error": None if passed else f"File missing: {path}",
            }
        if node_type == "file_content_assertion":
            path = Path(str(config.get("path", "")))
            expected = config.get("expected", "")
            if not path.exists():
                return {
                    "status": "failed",
                    "failure_classification": "file_missing",
                    "error": f"File missing: {path}",
                }
            content = path.read_text(encoding="utf-8", errors="replace")
            passed = expected in content if config.get("contains") else content == expected
            return {
                "status": "passed" if passed else "failed",
                "failure_classification": None if passed else "assertion_failure",
                "error": None if passed else "File content assertion failed",
                "outputs": {"passed": passed},
            }
        if node_type == "exit_code_assertion":
            expected = int(config.get("expected", 0))
            actual = int(config.get("actual", context.get("previous_result", {}).get("exitCode", -1)))
            passed = actual == expected
            return {
                "status": "passed" if passed else "failed",
                "outputs": {"expected": expected, "actual": actual},
                "failure_classification": None if passed else "cli_non_zero_exit_code",
                "error": None if passed else f"Exit code {actual} != {expected}",
            }
        if node_type == "numeric_threshold":
            value = float(config.get("value", 0))
            threshold = float(config.get("threshold", 0))
            op = config.get("operator", "lte")
            passed = _compare(value, threshold, op)
            return {
                "status": "passed" if passed else "failed",
                "outputs": {"value": value, "threshold": threshold},
                "failure_classification": None if passed else "assertion_failure",
                "error": None if passed else "Numeric threshold assertion failed",
            }
        if node_type == "json_assertion":
            actual = config.get("actual")
            expected = config.get("expected")
            passed = actual == expected
            return {
                "status": "passed" if passed else "failed",
                "failure_classification": None if passed else "assertion_failure",
                "error": None if passed else "JSON assertion failed",
                "outputs": {"expected": expected, "actual": actual},
            }
        return {"status": "failed", "error": f"Unknown validation node {node_type}"}


class EvidenceExecutor(NodeExecutor):
    node_types = {
        "capture_screenshot",
        "save_browser_trace",
        "save_console_logs",
        "save_network_logs",
        "save_cli_output",
        "collect_files",
        "create_execution_summary",
    }

    def execute(self, *, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        node_type = context.get("node_type", "create_execution_summary")
        summary = {
            "runId": str(context.get("run_id")),
            "nodeId": context.get("node_id"),
            "type": node_type,
            "note": config.get("note"),
            "collectedFrom": config.get("paths") or [],
        }
        return {
            "status": "passed",
            "outputs": {"summary": summary},
            "artifacts": [{"type": "summary", "name": f"{node_type}.json", "content": summary}],
        }


class IntegrationExecutor(NodeExecutor):
    node_types = {
        "create_workboard_item",
        "add_workboard_comment",
        "attach_execution_evidence",
        "send_webhook",
    }

    def execute(self, *, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        node_type = context.get("node_type", "send_webhook")
        if node_type == "send_webhook":
            url = config.get("url")
            if not url:
                return {
                    "status": "failed",
                    "failure_classification": "workflow_configuration_error",
                    "error": "Webhook URL required",
                }
            with httpx.Client(timeout=30) as client:
                response = client.post(url, json=config.get("payload") or context.get("payload") or {})
            return {
                "status": "passed" if response.is_success else "failed",
                "outputs": {"statusCode": response.status_code, "body": response.text[:2000]},
            }
        # Workboard-specific nodes are handled by dedicated service during failure flows;
        # keep node executors as structured placeholders that emit actionable payloads.
        return {
            "status": "passed",
            "outputs": {
                "queued": True,
                "action": node_type,
                "config": {k: v for k, v in config.items() if "password" not in k.lower()},
            },
        }


def _compare(left: Any, right: Any, op: str) -> bool:
    ops = {
        "eq": left == right,
        "neq": left != right,
        "gt": left > right if left is not None and right is not None else False,
        "gte": left >= right if left is not None and right is not None else False,
        "lt": left < right if left is not None and right is not None else False,
        "lte": left <= right if left is not None and right is not None else False,
        "contains": str(right) in str(left),
    }
    return bool(ops.get(op, left == right))


def _json_path(data: Any, path: str) -> Any:
    if not path:
        return data
    current = data
    for part in path.replace("[", ".").replace("]", "").split("."):
        if part == "":
            continue
        if isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def register_builtin_executors() -> None:
    from app.executors.auth_verification import AuthVerificationExecutor

    registry.register(LogicExecutor())
    registry.register(ApiExecutor())
    registry.register(DatabaseExecutor())
    registry.register(ValidationExecutor())
    registry.register(EvidenceExecutor())
    registry.register(IntegrationExecutor())
    registry.register(AuthVerificationExecutor())
