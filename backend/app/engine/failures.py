from __future__ import annotations

from dataclasses import dataclass


FAILURE_CATALOG: dict[str, dict[str, str]] = {
    "element_not_found": {
        "label": "Element not found",
        "action": "Update the locator or enable controlled healing with a high confidence threshold.",
    },
    "ambiguous_locator": {
        "label": "Ambiguous locator",
        "action": "Add a stable data-oneopen-id or tighten parent/nearby text context.",
    },
    "low_confidence_locator": {
        "label": "Low-confidence locator",
        "action": "Review suggested locators and approve a healed fingerprint before rerunning.",
    },
    "aspx_postback_timeout": {
        "label": "ASPX postback timeout",
        "action": "Increase postback wait timeout or wait for UpdatePanel completion.",
    },
    "react_render_timeout": {
        "label": "React render timeout",
        "action": "Wait for React render or loading indicators to disappear before interacting.",
    },
    "navigation_failure": {
        "label": "Navigation failure",
        "action": "Verify base URL, routing, and authentication state.",
    },
    "authentication_failure": {
        "label": "Authentication failure",
        "action": "Check credentials stored as secrets and login selectors.",
    },
    "api_failure": {
        "label": "API failure",
        "action": "Inspect status code, headers, and response body evidence.",
    },
    "database_validation_failure": {
        "label": "Database validation failure",
        "action": "Compare expected and actual query results and seed data.",
    },
    "cli_non_zero_exit_code": {
        "label": "CLI non-zero exit code",
        "action": "Inspect stdout/stderr and allowed exit codes.",
    },
    "command_timeout": {
        "label": "Command timeout",
        "action": "Increase timeout or split long-running commands.",
    },
    "file_missing": {
        "label": "File missing",
        "action": "Confirm artifact paths and working directory.",
    },
    "assertion_failure": {
        "label": "Assertion failure",
        "action": "Compare expected vs actual values and application build version.",
    },
    "agent_unavailable": {
        "label": "Agent unavailable",
        "action": "Ensure a matching browser/CLI agent is online with required tags.",
    },
    "infrastructure_error": {
        "label": "Infrastructure error",
        "action": "Check Redis, storage, and agent connectivity.",
    },
    "permission_denied": {
        "label": "Permission denied",
        "action": "Grant the required Flow permission or use a privileged agent profile.",
    },
    "workflow_configuration_error": {
        "label": "Workflow configuration error",
        "action": "Validate the workflow graph and node configuration.",
    },
}


@dataclass
class FailureInfo:
    code: str
    label: str
    message: str
    recommended_action: str


def classify_failure(code: str, message: str) -> FailureInfo:
    entry = FAILURE_CATALOG.get(code) or FAILURE_CATALOG["infrastructure_error"]
    return FailureInfo(
        code=code if code in FAILURE_CATALOG else "infrastructure_error",
        label=entry["label"],
        message=message,
        recommended_action=entry["action"],
    )
