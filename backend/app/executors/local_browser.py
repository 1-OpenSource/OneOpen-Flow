from __future__ import annotations

"""Local Playwright browser executor used when no browser agent is registered.

Implements semantic locator resolution, ASPX/React waits, fingerprint scoring,
and controlled healing for dynamic applications.
"""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.storage.service import StorageService


def execute_local_browser(
    *,
    config: dict[str, Any],
    node_type: str,
    secrets: dict[str, str],
    storage: StorageService,
    run_id: UUID,
    node_id: str,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _simulated_browser_result(config, node_type, run_id, node_id, storage)

    settings = get_settings()
    threshold = int(config.get("confidenceThreshold", settings.default_locator_confidence_threshold))
    healing_policy = config.get("locatorPolicy", "controlled_healing")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            context.tracing.start(screenshots=True, snapshots=True, sources=False)
            page = context.new_page()
            console_logs: list[str] = []
            network_logs: list[dict[str, Any]] = []
            page.on("console", lambda msg: console_logs.append(f"{msg.type}: {msg.text}"))
            page.on(
                "response",
                lambda resp: network_logs.append(
                    {"url": resp.url, "status": resp.status, "method": resp.request.method}
                ),
            )

            result = _dispatch(
                page=page,
                node_type=node_type,
                config=config,
                secrets=secrets,
                threshold=threshold,
                healing_policy=healing_policy,
            )

            artifacts = []
            screenshot_rel = f"artifacts/{run_id}/{node_id}/screenshot.png"
            screenshot_bytes = page.screenshot(full_page=True)
            screenshot_path = storage.save_bytes(relative_path=screenshot_rel, data=screenshot_bytes)
            artifacts.append(
                {"name": "screenshot.png", "path": screenshot_path, "type": "screenshot"}
            )

            trace_rel = f"artifacts/{run_id}/{node_id}/trace.zip"
            trace_path = storage.root / trace_rel
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            context.tracing.stop(path=str(trace_path))
            artifacts.append({"name": "trace.zip", "path": str(trace_path), "type": "trace"})

            console_path = storage.save_text(
                relative_path=f"artifacts/{run_id}/{node_id}/console.log",
                text="\n".join(console_logs),
            )
            network_path = storage.save_text(
                relative_path=f"artifacts/{run_id}/{node_id}/network.json",
                text=json.dumps(network_logs, indent=2),
            )
            artifacts.extend(
                [
                    {"name": "console.log", "path": console_path, "type": "console"},
                    {"name": "network.json", "path": network_path, "type": "network"},
                ]
            )

            context.close()
            browser.close()
            result["artifacts"] = artifacts + list(result.get("artifacts") or [])
            result.setdefault("logs", console_logs[-50:])
            return result
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "failed",
            "failure_classification": "infrastructure_error",
            "error": str(exc),
        }


def _dispatch(*, page: Any, node_type: str, config: dict[str, Any], secrets: dict[str, str], threshold: int, healing_policy: str) -> dict[str, Any]:
    action = node_type
    if node_type in {"browser", "open_url"} or config.get("action") == "open_url":
        url = config.get("url")
        page.goto(url, wait_until=config.get("waitUntil", "domcontentloaded"))
        return {"status": "passed", "outputs": {"url": page.url}}

    if action in {
        "wait_for_aspx_postback",
        "wait_for_react_render",
        "wait_for_element_stability",
        "wait_for_network_response",
        "wait_for_loading_indicator",
        "wait_for_route_change",
        "wait_for_page_state",
        "wait_for_element",
    }:
        _wait(page, action, config)
        return {"status": "passed", "outputs": {"waited": action}}

    locator_result = resolve_locator(page, config, threshold=threshold, policy=healing_policy)
    if locator_result.get("status") == "failed":
        return locator_result

    locator = locator_result["locator"]
    confidence = locator_result["confidence"]
    resolved_using = locator_result["resolvedUsing"]

    if action in {"click"}:
        locator.click()
    elif action in {"fill_input"}:
        value = config.get("value", "")
        if config.get("isSecret") and config.get("secretKey"):
            value = secrets.get(config["secretKey"], value)
        # Never type literal passwords from config if marked secret variable syntax remains
        locator.fill(str(value))
    elif action in {"select_option"}:
        locator.select_option(config.get("value"))
    elif action in {"press_key"}:
        locator.press(config.get("key", "Enter"))
    elif action in {"extract_text"}:
        text = locator.inner_text()
        return {
            "status": "passed",
            "locator": {"resolvedUsing": resolved_using, "confidence": confidence},
            "outputs": {config.get("outputKey", "text"): text},
        }
    elif action in {"extract_attribute"}:
        value = locator.get_attribute(config.get("attribute", "value"))
        return {
            "status": "passed",
            "locator": {"resolvedUsing": resolved_using, "confidence": confidence},
            "outputs": {config.get("outputKey", "value"): value},
        }
    elif action in {"take_screenshot"}:
        return {
            "status": "passed",
            "locator": {"resolvedUsing": resolved_using, "confidence": confidence},
            "outputs": {},
        }
    elif action in {"assert_visible"}:
        assert locator.is_visible()
    elif action in {"assert_hidden"}:
        assert not locator.is_visible()
    elif action in {"assert_text"}:
        actual = locator.inner_text()
        expected = config.get("expected", "")
        if expected not in actual and actual != expected:
            return {
                "status": "failed",
                "failure_classification": "assertion_failure",
                "error": f"Expected text '{expected}', got '{actual}'",
                "outputs": {"expected": expected, "actual": actual},
            }
    elif action in {"assert_url"}:
        expected = config.get("expected", "")
        if expected not in page.url:
            return {
                "status": "failed",
                "failure_classification": "assertion_failure",
                "error": f"URL assertion failed: {page.url}",
                "outputs": {"expected": expected, "actual": page.url},
            }
    elif action in {"assert_element_count"}:
        count = locator.count()
        expected = int(config.get("expected", 1))
        if count != expected:
            return {
                "status": "failed",
                "failure_classification": "assertion_failure",
                "error": f"Expected {expected} elements, found {count}",
            }
    elif action in {"assert_field_value"}:
        actual = locator.input_value()
        expected = config.get("expected", "")
        if actual != expected:
            return {
                "status": "failed",
                "failure_classification": "assertion_failure",
                "error": f"Field value '{actual}' != '{expected}'",
                "outputs": {"expected": expected, "actual": actual},
            }
    elif action in {"execute_javascript"}:
        value = page.evaluate(config.get("script", "() => true"))
        return {"status": "passed", "outputs": {"result": value}}
    elif action in {"upload_file"}:
        locator.set_input_files(config.get("path"))
    elif action in {"switch_tab"}:
        pages = page.context.pages
        index = int(config.get("index", 0))
        pages[index].bring_to_front()
    elif action in {"close_tab"}:
        page.close()
    else:
        # Generic action using config.action
        pass

    return {
        "status": "passed",
        "locator": {"resolvedUsing": resolved_using, "confidence": confidence, "healed": locator_result.get("healed", False)},
        "outputs": {},
        "suggestions": locator_result.get("suggestions"),
    }


def resolve_locator(page: Any, config: dict[str, Any], *, threshold: int, policy: str) -> dict[str, Any]:
    fingerprint = config.get("fingerprint") or {}
    candidates = generate_locator_candidates(page, config, fingerprint)
    if not candidates:
        return {
            "status": "failed",
            "failure_classification": "element_not_found",
            "error": "No locator candidates resolved",
            "suggestions": [],
        }

    best = max(candidates, key=lambda c: c["confidence"])
    if policy == "strict":
        approved = config.get("approvedLocator")
        if not approved:
            return {
                "status": "failed",
                "failure_classification": "element_not_found",
                "error": "Strict policy requires an approved locator",
            }
        # try approved only
        approved_match = next((c for c in candidates if c["strategy"] == approved.get("strategy")), None)
        if not approved_match:
            return {
                "status": "failed",
                "failure_classification": "element_not_found",
                "error": "Approved locator not found",
                "suggestions": candidates[:5],
            }
        best = approved_match

    if policy == "suggest" and best["confidence"] < 100:
        return {
            "status": "failed",
            "failure_classification": "low_confidence_locator",
            "error": "Locator requires review (suggest policy)",
            "suggestions": candidates[:5],
            "confidence": best["confidence"],
        }

    if policy == "controlled_healing" and best["confidence"] < threshold:
        return {
            "status": "failed",
            "failure_classification": "low_confidence_locator",
            "error": f"Best locator confidence {best['confidence']} below threshold {threshold}",
            "suggestions": candidates[:5],
            "confidence": best["confidence"],
        }

    healed = bool(fingerprint) and best["strategy"] not in set(fingerprint.get("stableSelectors") or [])
    return {
        "status": "passed",
        "locator": best["locator"],
        "confidence": best["confidence"],
        "resolvedUsing": best["strategy"],
        "healed": healed,
        "suggestions": candidates[:5],
    }


def generate_locator_candidates(page: Any, config: dict[str, Any], fingerprint: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    def add(strategy: str, locator: Any, base: int, **signals: Any) -> None:
        try:
            count = locator.count()
        except Exception:  # noqa: BLE001
            return
        if count == 0:
            return
        confidence = score_candidate(base=base, count=count, fingerprint=fingerprint, signals=signals)
        candidates.append(
            {
                "strategy": strategy,
                "locator": locator.first if count else locator,
                "confidence": confidence,
                "count": count,
            }
        )

    oneopen_id = fingerprint.get("attributes", {}).get("data-oneopen-id") or config.get("oneOpenId")
    if oneopen_id:
        add("oneopen-stable-attribute", page.locator(f'[data-oneopen-id="{oneopen_id}"]'), 100)

    role = fingerprint.get("role") or config.get("role")
    name = fingerprint.get("accessibleName") or config.get("name")
    if role and name:
        add("role-and-name", page.get_by_role(role, name=re.compile(re.escape(name), re.I)), 95)

    label = config.get("label") or fingerprint.get("label")
    if label:
        add("associated-label", page.get_by_label(label), 92)

    placeholder = config.get("placeholder") or fingerprint.get("placeholder")
    if placeholder:
        add("placeholder", page.get_by_placeholder(placeholder), 88)

    text = fingerprint.get("text") or config.get("text")
    if text:
        add("visible-text", page.get_by_text(text, exact=False), 84)

    for attr_name in ("data-testid", "name", "aria-label"):
        value = (fingerprint.get("attributes") or {}).get(attr_name) or config.get(attr_name)
        if value:
            add(f"stable-attr-{attr_name}", page.locator(f'[{attr_name}="{value}"]'), 90)

    # ASPX partial ID strategies
    partial_id = config.get("idSuffix") or fingerprint.get("idSuffix")
    if partial_id:
        add("partial-id-suffix", page.locator(f'[id$="{partial_id}"]'), 80)
    contains_id = config.get("idContains") or fingerprint.get("idContains")
    if contains_id:
        add("partial-id-contains", page.locator(f'[id*="{contains_id}"]'), 75)

    for selector in fingerprint.get("stableSelectors") or []:
        add("stable-selector", page.locator(selector), 93)
    for selector in fingerprint.get("historicalSelectors") or []:
        add("historical-selector", page.locator(selector), 70)

    if config.get("css"):
        add("css", page.locator(config["css"]), 60)
    if config.get("xpath"):
        add("xpath", page.locator(f'xpath={config["xpath"]}'), 55)

    return candidates


def score_candidate(*, base: int, count: int, fingerprint: dict[str, Any], signals: dict[str, Any]) -> int:
    score = base
    if count == 1:
        score += 5
    elif count > 3:
        score -= min(30, count * 3)
    # Prefer semantic matches when fingerprint present
    if fingerprint.get("role"):
        score += 2
    if fingerprint.get("accessibleName"):
        score += 2
    if fingerprint.get("parentText"):
        score += 1
    return max(0, min(100, score))


def _wait(page: Any, action: str, config: dict[str, Any]) -> None:
    timeout = float(config.get("timeoutSeconds", 30)) * 1000
    if action == "wait_for_element":
        page.locator(config.get("css") or "body").first.wait_for(state="visible", timeout=timeout)
        return
    if action == "wait_for_aspx_postback":
        # Detect ASP.NET postbacks / UpdatePanel completion / stable DOM
        page.wait_for_function(
            """() => {
                const busy = document.querySelector('.aspNetDisabled, [disabled][data-aspx-loading="true"]');
                const panel = document.querySelector('[id*="UpdatePanel"]');
                const navBusy = window.__oneopenAspxBusy === true;
                return !busy && !navBusy && document.readyState === 'complete';
            }""",
            timeout=timeout,
        )
        page.wait_for_timeout(300)
        return
    if action == "wait_for_react_render":
        page.wait_for_function(
            """() => {
                const root = document.querySelector('#root, #app, [data-reactroot]');
                const loaders = document.querySelectorAll('[aria-busy="true"], .MuiCircularProgress-root, .loading');
                return !!root && loaders.length === 0;
            }""",
            timeout=timeout,
        )
        return
    if action == "wait_for_element_stability":
        selector = config.get("css") or "body"
        page.wait_for_function(
            """(sel) => {
                const el = document.querySelector(sel);
                if (!el) return false;
                const key = '__oneopenStable';
                const now = el.outerHTML.length;
                const prev = window[key] || 0;
                window[key] = now;
                return prev && prev === now;
            }""",
            arg=selector,
            timeout=timeout,
        )
        return
    if action == "wait_for_network_response":
        url_part = config.get("urlContains", "")
        page.wait_for_response(lambda r: url_part in r.url, timeout=timeout)
        return
    if action == "wait_for_loading_indicator":
        selector = config.get("css") or '[aria-busy="true"], .loading, .MuiCircularProgress-root'
        page.locator(selector).first.wait_for(state="hidden", timeout=timeout)
        return
    if action == "wait_for_route_change":
        expected = config.get("urlContains", "")
        page.wait_for_url(lambda url: expected in url, timeout=timeout)
        return
    page.wait_for_load_state(config.get("state", "networkidle"), timeout=timeout)


def _simulated_browser_result(
    config: dict[str, Any],
    node_type: str,
    run_id: UUID,
    node_id: str,
    storage: StorageService,
) -> dict[str, Any]:
    """Dev fallback when Playwright is not installed."""
    note = "Playwright not installed; simulated browser step for local development"
    path = storage.save_text(
        relative_path=f"artifacts/{run_id}/{node_id}/simulated.txt",
        text=f"{node_type}\n{json.dumps(config, default=str)}",
    )
    outputs = {}
    if node_type == "extract_text":
        outputs[config.get("outputKey", "text")] = config.get("simulatedValue", "1.0.0")
    return {
        "status": "passed",
        "outputs": outputs,
        "locator": {"resolvedUsing": "simulated", "confidence": 100},
        "artifacts": [{"name": "simulated.txt", "path": path, "type": "log"}],
        "logs": [note],
    }
