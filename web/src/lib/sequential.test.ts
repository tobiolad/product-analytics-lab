import { describe, expect, it } from "vitest";
import { sequentialStep, sequentialTextColor } from "./sequential";

describe("sequentialStep", () => {
  it("maps the minimum of the range to the lightest step", () => {
    expect(sequentialStep(0)).toBe("var(--seq-100)");
  });

  it("maps the maximum of the range to the darkest step", () => {
    expect(sequentialStep(1)).toBe("var(--seq-700)");
  });

  it("is monotonic -- a higher value never maps to a lighter step", () => {
    const steps = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1].map((v) => sequentialStep(v));
    const order = ["100", "150", "200", "250", "300", "350", "400", "450", "500", "550", "600", "650", "700"];
    let lastIdx = -1;
    for (const step of steps) {
      const idx = order.indexOf(step.match(/seq-(\d+)/)![1]);
      expect(idx).toBeGreaterThanOrEqual(lastIdx);
      lastIdx = idx;
    }
  });

  it("clamps values outside the given [min, max] range instead of extrapolating", () => {
    expect(sequentialStep(-5)).toBe(sequentialStep(0));
    expect(sequentialStep(50)).toBe(sequentialStep(1));
  });
});

describe("sequentialTextColor", () => {
  it("uses dark text on the lightest steps", () => {
    expect(sequentialTextColor(0)).toBe("#0b0b0b");
  });

  it("uses white text on the darkest steps", () => {
    expect(sequentialTextColor(1)).toBe("#ffffff");
  });
});
