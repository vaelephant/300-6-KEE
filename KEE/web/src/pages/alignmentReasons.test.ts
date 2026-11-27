import { describe, expect, it } from "vitest";
import { reasonCodeLabel, validationDecisionLabel } from "./alignmentReasons";

describe("OR-01 reason code labels", () => {
  it("maps closed codes in both languages", () => {
    expect(reasonCodeLabel("DOMAIN_MISMATCH", "zh")).toContain("定义域");
    expect(reasonCodeLabel("DOMAIN_MISMATCH", "en")).toContain("domain");
    expect(reasonCodeLabel("AMBIGUOUS_BINDING", "en")).toContain("Ambiguous");
  });

  it("falls back to the raw code when unknown", () => {
    expect(reasonCodeLabel("NOT_A_REAL_CODE", "en")).toBe("NOT_A_REAL_CODE");
  });

  it("labels validation decisions", () => {
    expect(validationDecisionLabel("needs_review", "zh")).toBe("需人工审核");
    expect(validationDecisionLabel("rejected", "en")).toBe("Validation rejected");
    expect(validationDecisionLabel(null, "en")).toBeNull();
  });
});
