import { create } from "zustand";
import type { Edge, Node } from "@xyflow/react";
import type { WorkflowDefinition, WorkflowNodeDef } from "../types";

type StudioState = {
  workflowId?: string;
  name: string;
  description: string;
  variables: Record<string, unknown>;
  selectedNodeId?: string;
  validationErrors: string[];
  setMeta: (name: string, description: string) => void;
  setVariables: (variables: Record<string, unknown>) => void;
  selectNode: (id?: string) => void;
  loadDefinitionMeta: (workflowId: string, definition: WorkflowDefinition) => void;
  setValidationErrors: (errors: string[]) => void;
};

export function categoryFor(type: string): string {
  if (
    [
      "wait_for_email",
      "extract_email_otp",
      "extract_email_verification_link",
      "open_verification_link",
      "generate_totp",
      "verify_totp",
      "human_otp_input",
      "fill_otp",
    ].includes(type)
  ) {
    return "auth";
  }
  if (type.startsWith("run_") || type === "cli") return "cli";
  if (
    [
      "open_url",
      "click",
      "fill_input",
      "select_option",
      "press_key",
      "wait_for_element",
      "wait_for_page_state",
      "wait_for_aspx_postback",
      "wait_for_react_render",
      "extract_text",
      "extract_attribute",
      "take_screenshot",
      "assert_visible",
      "assert_text",
      "assert_url",
      "execute_javascript",
      "browser",
    ].includes(type) ||
    type.startsWith("wait_for_") ||
    type.startsWith("assert_")
  ) {
    if (
      type.startsWith("assert_") &&
      ["assert_visible", "assert_hidden", "assert_text", "assert_url", "assert_element_count", "assert_field_value"].includes(type)
    ) {
      return "browser";
    }
    if (type.startsWith("assert_")) return "validation";
    return "browser";
  }
  if (type.startsWith("rest_") || type.includes("json") || type === "assert_status_code") return "api";
  if (type.includes("query") || type.includes("row") || type.includes("column") || type.startsWith("execute_")) {
    return "database";
  }
  if (type.includes("workboard") || type.includes("webhook")) return "integration";
  if (
    type.includes("screenshot") ||
    type.includes("trace") ||
    type.includes("logs") ||
    type.includes("collect") ||
    type.includes("summary") ||
    type.includes("cli_output")
  ) {
    return "evidence";
  }
  if (
    ["compare_values", "regex_match", "json_assertion", "file_exists", "file_content_assertion", "exit_code_assertion", "numeric_threshold"].includes(
      type,
    )
  ) {
    return "validation";
  }
  return "logic";
}

export function definitionToFlow(definition: WorkflowDefinition): { nodes: Node[]; edges: Edge[] } {
  return {
    nodes: definition.nodes.map((n: WorkflowNodeDef) => ({
      id: n.id,
      type: "flowNode",
      position: n.position,
      data: {
        label: n.name,
        nodeType: n.type,
        config: n.config,
        category: categoryFor(n.type),
        status: "idle",
      },
    })),
    edges: definition.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle || undefined,
      targetHandle: e.targetHandle || undefined,
      label: e.label || undefined,
    })),
  };
}

export function flowToDefinition(
  meta: { id?: string; name: string; description: string; variables: Record<string, unknown> },
  nodes: Node[],
  edges: Edge[],
): WorkflowDefinition {
  return {
    id: meta.id,
    name: meta.name,
    version: 1,
    description: meta.description,
    variables: meta.variables,
    nodes: nodes.map((n) => ({
      id: n.id,
      type: String(n.data.nodeType),
      name: String(n.data.label),
      config: (n.data.config as Record<string, unknown>) || {},
      position: n.position,
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle,
      targetHandle: e.targetHandle,
      label: typeof e.label === "string" ? e.label : null,
    })),
  };
}

export const useStudioStore = create<StudioState>((set, get) => ({
  name: "Untitled workflow",
  description: "",
  variables: {},
  validationErrors: [],
  setMeta: (name, description) => set({ name, description }),
  setVariables: (variables) => set({ variables }),
  selectNode: (id) => {
    if (get().selectedNodeId === id) return;
    set({ selectedNodeId: id });
  },
  loadDefinitionMeta: (workflowId, definition) =>
    set({
      workflowId,
      name: definition.name,
      description: definition.description || "",
      variables: definition.variables || {},
      selectedNodeId: undefined,
      validationErrors: [],
    }),
  setValidationErrors: (errors) => set({ validationErrors: errors }),
}));
