import { describe, expect, it } from "vitest";

import { stepNumberOnWheel, stepSelectOnWheel } from "./wheelInput";

describe("wheelInput", () => {
  it("steps numbers within bounds", () => {
    expect(stepNumberOnWheel(-1, 50, 5, 200)).toBe(51);
    expect(stepNumberOnWheel(1, 50, 5, 200)).toBe(49);
    expect(stepNumberOnWheel(-1, 200, 5, 200)).toBe(200);
    expect(stepNumberOnWheel(1, 5, 5, 200)).toBe(5);
  });

  it("cycles select options", () => {
    const options = ["a", "b", "c"];
    expect(stepSelectOnWheel(-1, "b", options)).toBe("a");
    expect(stepSelectOnWheel(1, "b", options)).toBe("c");
    expect(stepSelectOnWheel(1, "c", options)).toBe("a");
  });
});
