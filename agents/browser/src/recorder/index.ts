/**
 * Browser recorder: converts Playwright interactions into workflow nodes.
 * Passwords are never recorded as plaintext — they become {{secret.*}} variables.
 */

export type RecordedAction = {
  type: string;
  name: string;
  config: Record<string, unknown>;
};

export function actionToNode(action: {
  kind: "navigate" | "click" | "fill" | "select" | "upload" | "download" | "tab";
  url?: string;
  role?: string;
  name?: string;
  label?: string;
  value?: string;
  isPassword?: boolean;
  fingerprint?: Record<string, unknown>;
}): RecordedAction {
  switch (action.kind) {
    case "navigate":
      return {
        type: "open_url",
        name: `Open ${action.url}`,
        config: { url: action.url },
      };
    case "click":
      return {
        type: "click",
        name: `Click ${action.name || action.label || "element"}`,
        config: {
          role: action.role,
          name: action.name,
          label: action.label,
          fingerprint: action.fingerprint,
        },
      };
    case "fill": {
      const value = action.isPassword
        ? "{{secret.LOGIN_PASSWORD}}"
        : action.value;
      return {
        type: "fill_input",
        name: `Fill ${action.label || action.name || "input"}`,
        config: {
          label: action.label,
          value,
          isSecret: !!action.isPassword,
          secretKey: action.isPassword ? "LOGIN_PASSWORD" : undefined,
          fingerprint: action.fingerprint,
        },
      };
    }
    case "select":
      return {
        type: "select_option",
        name: `Select ${action.label || "option"}`,
        config: { label: action.label, value: action.value, fingerprint: action.fingerprint },
      };
    case "upload":
      return {
        type: "upload_file",
        name: "Upload file",
        config: { path: action.value, fingerprint: action.fingerprint },
      };
    case "download":
      return {
        type: "download_file",
        name: "Download file",
        config: {},
      };
    case "tab":
      return {
        type: "switch_tab",
        name: "Switch tab",
        config: { index: Number(action.value || 0) },
      };
    default:
      return { type: "wait", name: "Recorded pause", config: { seconds: 1 } };
  }
}

export function buildFingerprint(el: {
  role?: string;
  accessibleName?: string;
  text?: string;
  tag?: string;
  parentText?: string;
  nearbyText?: string[];
  attributes?: Record<string, string>;
  historicalSelectors?: string[];
}) {
  const stableSelectors = el.attributes?.["data-oneopen-id"]
    ? [`[data-oneopen-id='${el.attributes["data-oneopen-id"]}']`]
    : [];
  return {
    strategy: "fingerprint",
    role: el.role,
    accessibleName: el.accessibleName,
    text: el.text,
    tag: el.tag,
    parentText: el.parentText,
    nearbyText: el.nearbyText || [],
    attributes: el.attributes || {},
    stableSelectors,
    historicalSelectors: el.historicalSelectors || [],
  };
}
