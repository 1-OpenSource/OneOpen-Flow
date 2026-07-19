import { describe, expect, it } from "vitest";
import { scoreCandidate } from "./locators";

describe("locator confidence", () => {
  it("scores unique semantic matches highly", () => {
    const score = scoreCandidate({
      base: 95,
      count: 1,
      fingerprint: { role: "button", accessibleName: "Save" },
      signals: {},
    });
    expect(score).toBeGreaterThanOrEqual(90);
  });

  it("penalizes ambiguous matches", () => {
    const score = scoreCandidate({
      base: 80,
      count: 8,
      fingerprint: {},
      signals: {},
    });
    expect(score).toBeLessThan(80);
  });
});
