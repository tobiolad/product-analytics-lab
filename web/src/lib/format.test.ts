import { describe, expect, it } from "vitest";
import { num, pct, shortDate, signedPct } from "./format";

describe("pct", () => {
  it("formats a fraction as a rounded percentage", () => {
    expect(pct(0.2956)).toBe("29.6%");
  });

  it("supports a custom digit count", () => {
    expect(pct(0.2956, 0)).toBe("30%");
  });

  it("returns an em dash for null/undefined/NaN", () => {
    expect(pct(null)).toBe("—");
    expect(pct(undefined)).toBe("—");
    expect(pct(NaN)).toBe("—");
  });
});

describe("signedPct", () => {
  it("prefixes a positive value with +", () => {
    expect(signedPct(0.112)).toBe("+11.2%");
  });

  it("does not double up the minus sign on negative values", () => {
    expect(signedPct(-0.05)).toBe("-5.0%");
  });

  it("treats exactly zero as unsigned", () => {
    expect(signedPct(0)).toBe("0.0%");
  });
});

describe("num", () => {
  it("adds thousands separators", () => {
    expect(num(2000)).toBe("2,000");
  });

  it("returns an em dash for missing values", () => {
    expect(num(null)).toBe("—");
    expect(num(undefined)).toBe("—");
  });
});

describe("shortDate", () => {
  it("formats an ISO date as a short month name and day", () => {
    expect(shortDate("2026-06-15T00:00:00Z")).toMatch(/Jun 1[45]/); // tz-dependent day boundary
  });

  it("passes through a value it can't parse as a date", () => {
    expect(shortDate("not-a-date")).toBe("not-a-date");
  });
});
