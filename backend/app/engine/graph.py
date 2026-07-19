from __future__ import annotations

import re
from typing import Any

from app.schemas import ValidationIssue, ValidationResult, WorkflowDefinition

LOGIC_LOOP_TYPES = {"loop", "for_each", "retry"}
REQUIRED_START = "start"
REQUIRED_END = "end"


def validate_workflow_graph(definition: WorkflowDefinition) -> ValidationResult:
    issues: list[ValidationIssue] = []
    node_ids = {node.id for node in definition.nodes}
    node_by_id = {node.id: node for node in definition.nodes}

    if not definition.nodes:
        issues.append(
            ValidationIssue(
                severity="error",
                code="empty_workflow",
                message="Workflow must contain at least one node",
            )
        )
        return ValidationResult(valid=False, issues=issues)

    start_nodes = [n for n in definition.nodes if n.type == REQUIRED_START]
    end_nodes = [n for n in definition.nodes if n.type == REQUIRED_END]
    if len(start_nodes) != 1:
        issues.append(
            ValidationIssue(
                severity="error",
                code="start_required",
                message="Workflow must contain exactly one Start node",
            )
        )
    if len(end_nodes) < 1:
        issues.append(
            ValidationIssue(
                severity="error",
                code="end_required",
                message="Workflow must contain at least one End node",
            )
        )

    for edge in definition.edges:
        if edge.source not in node_ids:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="invalid_edge_source",
                    message=f"Edge {edge.id} references missing source {edge.source}",
                )
            )
        if edge.target not in node_ids:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="invalid_edge_target",
                    message=f"Edge {edge.id} references missing target {edge.target}",
                )
            )

    adjacency: dict[str, list[str]] = {node.id: [] for node in definition.nodes}
    incoming: dict[str, int] = {node.id: 0 for node in definition.nodes}
    for edge in definition.edges:
        if edge.source in adjacency and edge.target in adjacency:
            adjacency[edge.source].append(edge.target)
            incoming[edge.target] += 1

    # Detect cycles that are not explicitly represented by loop nodes.
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node_id: str, path: list[str]) -> None:
        if node_id in visiting:
            cycle_start = path.index(node_id)
            cycle_nodes = path[cycle_start:]
            if not any(node_by_id[n].type in LOGIC_LOOP_TYPES for n in cycle_nodes):
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="unexpected_cycle",
                        message=f"Cycle detected without loop node: {' -> '.join(cycle_nodes + [node_id])}",
                        node_id=node_id,
                    )
                )
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        for nxt in adjacency.get(node_id, []):
            dfs(nxt, path + [node_id])
        visiting.remove(node_id)
        visited.add(node_id)

    for node in definition.nodes:
        dfs(node.id, [])

    # Reachability from start
    if start_nodes:
        reachable: set[str] = set()
        stack = [start_nodes[0].id]
        while stack:
            current = stack.pop()
            if current in reachable:
                continue
            reachable.add(current)
            stack.extend(adjacency.get(current, []))
        for node in definition.nodes:
            if node.id not in reachable and node.type != REQUIRED_START:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="disconnected_node",
                        message=f"Node '{node.name}' is not reachable from Start",
                        node_id=node.id,
                    )
                )

    for node in definition.nodes:
        if node.type.startswith("cli") or node.type in {
            "run_bash",
            "run_powershell",
            "run_cmd",
            "run_python_script",
            "run_node_command",
            "run_custom_executable",
        }:
            command = node.config.get("command")
            if not command:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="missing_command",
                        message=f"CLI node '{node.name}' requires a command",
                        node_id=node.id,
                    )
                )

    error_issues = [i for i in issues if i.severity == "error"]
    return ValidationResult(valid=len(error_issues) == 0, issues=issues)


VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_./-]+)\s*\}\}")


def resolve_variables(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str):
        def replacer(match: re.Match[str]) -> str:
            path = match.group(1)
            resolved = _lookup(context, path)
            return "" if resolved is None else str(resolved)

        if VARIABLE_PATTERN.fullmatch(value.strip()):
            path = VARIABLE_PATTERN.fullmatch(value.strip()).group(1)  # type: ignore[union-attr]
            return _lookup(context, path)
        return VARIABLE_PATTERN.sub(replacer, value)
    if isinstance(value, list):
        return [resolve_variables(item, context) for item in value]
    if isinstance(value, dict):
        return {k: resolve_variables(v, context) for k, v in value.items()}
    return value


def _lookup(context: dict[str, Any], path: str) -> Any:
    parts = path.split(".")
    current: Any = context
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def build_variable_context(
    *,
    variables: dict[str, Any],
    secrets: dict[str, Any],
    node_outputs: dict[str, Any],
    runtime: dict[str, Any] | None = None,
    loop: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "variable": variables,
        "secret": secrets,
        "node": node_outputs,
        "runtime": runtime or {},
        "loop": loop or {},
    }
