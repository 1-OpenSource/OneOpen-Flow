import { describe, expect, it } from "vitest";
import { categoryFor } from "../src/stores/studioStore";
import { NODE_PALETTE } from "../src/components/flow/palette";

describe("flow studio helpers", () => {
  it("categorizes node types", () => {
    expect(categoryFor("run_powershell")).toBe("cli");
    expect(categoryFor("open_url")).toBe("browser");
    expect(categoryFor("rest_request")).toBe("api");
    expect(categoryFor("compare_values")).toBe("validation");
    expect(categoryFor("start")).toBe("logic");
  });

  it("includes required palette categories", () => {
    const categories = new Set(NODE_PALETTE.map((n) => n.category));
    for (const required of ["Browser", "CLI", "API", "Database", "Files", "Logic", "Validation", "Evidence", "Integration", "Auth"]) {
      expect(categories.has(required)).toBe(true);
    }
  });
});
