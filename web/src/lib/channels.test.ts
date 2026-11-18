import { describe, expect, it } from "vitest";
import { CHANNEL_ORDER, channelColor, channelLabel } from "./channels";

describe("channelLabel", () => {
  it("maps known channel keys to a human label", () => {
    expect(channelLabel("organic_search")).toBe("Organic search");
    expect(channelLabel("content_marketing")).toBe("Content marketing");
  });

  it("falls back to the raw value for an unknown channel", () => {
    expect(channelLabel("some_new_channel")).toBe("some_new_channel");
  });

  it("labels null/undefined as Unknown", () => {
    expect(channelLabel(null)).toBe("Unknown");
    expect(channelLabel(undefined)).toBe("Unknown");
  });
});

describe("channelColor", () => {
  it("assigns every known channel a distinct color", () => {
    const colors = new Set(CHANNEL_ORDER.map((c) => channelColor(c)));
    expect(colors.size).toBe(CHANNEL_ORDER.length);
  });

  it("gives null/unknown a dedicated muted color, never a series color", () => {
    const seriesColors = new Set(CHANNEL_ORDER.map((c) => channelColor(c)));
    expect(seriesColors.has(channelColor(null))).toBe(false);
  });
});
