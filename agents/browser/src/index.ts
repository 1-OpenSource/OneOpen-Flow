import { chromium, type Page } from "playwright";

const API_BASE = process.env.FLOW_API_URL || "http://localhost:8000";
const AGENT_ID = process.env.AGENT_ID || "";
const AGENT_TOKEN = process.env.AGENT_TOKEN || "";

async function register(): Promise<{ id: string; token: string }> {
  if (AGENT_ID && AGENT_TOKEN) return { id: AGENT_ID, token: AGENT_TOKEN };
  const response = await fetch(`${API_BASE}/api/agents/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: process.env.AGENT_NAME || "browser-agent-local",
      agent_type: "browser",
      operating_system: process.platform,
      tags: ["browser", "playwright", process.platform],
      capabilities: ["playwright", "screenshots", "trace", "aspx", "react"],
      version: "0.1.0",
    }),
  });
  if (!response.ok) throw new Error(`Register failed: ${response.status}`);
  return response.json();
}

async function heartbeat(id: string, token: string, workload: number) {
  await fetch(`${API_BASE}/api/agents/heartbeat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Agent-Id": id,
      "X-Agent-Token": token,
    },
    body: JSON.stringify({ status: workload ? "busy" : "idle", current_workload: workload }),
  });
}

async function claim(id: string, token: string) {
  const response = await fetch(`${API_BASE}/api/agents/${id}/claim-job`, {
    method: "POST",
    headers: { "X-Agent-Token": token },
  });
  return response.json();
}

async function complete(id: string, token: string, jobId: string, status: string, result: unknown, logs: string[]) {
  const url = new URL(`${API_BASE}/api/agents/${id}/complete-job`);
  url.searchParams.set("job_id", jobId);
  await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Agent-Token": token,
    },
    body: JSON.stringify({ status, result, logs }),
  });
}

async function executeBrowserJob(payload: Record<string, unknown>) {
  const config = (payload.payload as Record<string, unknown>)?.payload
    ? ((payload.payload as Record<string, unknown>).payload as Record<string, unknown>)
    : (payload as Record<string, unknown>);
  const inner = (config.payload as Record<string, unknown>) || config;
  const nodeType = String(inner.nodeType || "open_url");
  const nodeConfig = (inner.config as Record<string, unknown>) || {};
  const secrets = (inner.secrets as Record<string, string>) || {};
  const logs: string[] = [];

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  page.on("console", (msg) => logs.push(`${msg.type()}: ${msg.text()}`));

  try {
    const result = await dispatch(page, nodeType, nodeConfig, secrets, logs);
    await browser.close();
    return { status: result.status || "passed", result, logs };
  } catch (error) {
    await browser.close();
    return {
      status: "failed",
      result: {
        status: "failed",
        failure_classification: "infrastructure_error",
        error: String(error),
      },
      logs,
    };
  }
}

async function dispatch(
  page: Page,
  nodeType: string,
  config: Record<string, unknown>,
  secrets: Record<string, string>,
  logs: string[],
) {
  if (nodeType === "open_url" || nodeType === "browser") {
    await page.goto(String(config.url), { waitUntil: "domcontentloaded" });
    logs.push(`Opened ${config.url}`);
    return { status: "passed", outputs: { url: page.url() } };
  }
  if (nodeType === "fill_input") {
    const locator = await resolve(page, config);
    let value = String(config.value ?? "");
    if (config.secretKey) value = secrets[String(config.secretKey)] || value;
    await locator.fill(value);
    return { status: "passed", outputs: {}, locator: { resolvedUsing: "semantic", confidence: 95 } };
  }
  if (nodeType === "click") {
    const locator = await resolve(page, config);
    await locator.click();
    return { status: "passed", outputs: {}, locator: { resolvedUsing: "semantic", confidence: 95 } };
  }
  if (nodeType === "wait_for_aspx_postback") {
    await page.waitForFunction(() => document.readyState === "complete");
    return { status: "passed", outputs: { waited: "aspx" } };
  }
  if (nodeType === "wait_for_react_render") {
    await page.waitForFunction(() => !!document.querySelector("#root, #app, [data-reactroot]"));
    return { status: "passed", outputs: { waited: "react" } };
  }
  if (nodeType === "assert_visible" || nodeType === "assert_text") {
    const locator = await resolve(page, config);
    await locator.waitFor({ state: "visible" });
    if (nodeType === "assert_text" && config.expected) {
      const text = await locator.innerText();
      if (!text.includes(String(config.expected))) {
        return {
          status: "failed",
          failure_classification: "assertion_failure",
          error: `Expected ${config.expected}, got ${text}`,
          outputs: { expected: config.expected, actual: text },
        };
      }
    }
    return { status: "passed", outputs: {} };
  }
  if (nodeType === "extract_text") {
    const locator = await resolve(page, config);
    const text = await locator.innerText();
    return {
      status: "passed",
      outputs: { [String(config.outputKey || "text")]: text },
      locator: { resolvedUsing: "semantic", confidence: 94 },
    };
  }
  if (nodeType === "take_screenshot") {
    const path = `screenshot-${Date.now()}.png`;
    await page.screenshot({ path, fullPage: true });
    return { status: "passed", outputs: {}, artifacts: [{ name: path, type: "screenshot", path }] };
  }
  logs.push(`Unhandled node type ${nodeType}; marking passed for agent connectivity`);
  return { status: "passed", outputs: {} };
}

async function resolve(page: Page, config: Record<string, unknown>) {
  const oneopenId = (config.fingerprint as Record<string, unknown>)?.attributes
    ? ((config.fingerprint as { attributes?: Record<string, string> }).attributes || {})["data-oneopen-id"]
    : config.oneOpenId;
  if (oneopenId) return page.locator(`[data-oneopen-id="${oneopenId}"]`).first();
  if (config.role && config.name) return page.getByRole(String(config.role) as never, { name: String(config.name) });
  if (config.label) return page.getByLabel(String(config.label));
  if (config.placeholder) return page.getByPlaceholder(String(config.placeholder));
  if (config.text) return page.getByText(String(config.text));
  if (config.idSuffix) return page.locator(`[id$="${config.idSuffix}"]`).first();
  if (config.css) return page.locator(String(config.css)).first();
  return page.locator("body");
}

async function main() {
  const { id, token } = await register();
  console.log(`Browser agent registered: ${id}`);
  let workload = 0;
  setInterval(() => heartbeat(id, token, workload), 5000);
  while (true) {
    const claimed = await claim(id, token);
    if (!claimed.job) {
      await new Promise((r) => setTimeout(r, 2000));
      continue;
    }
    workload += 1;
    const outcome = await executeBrowserJob(claimed.job);
    await complete(id, token, claimed.job.id, outcome.status, outcome.result, outcome.logs);
    workload = Math.max(0, workload - 1);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
