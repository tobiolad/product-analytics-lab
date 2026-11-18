// Sequential blue ramp (light->dark, magnitude encoding) -- see
// theme.css / palette.md. Values are fixed named steps, never a freehand
// interpolation, so every heatmap in the app buckets into the same scale.
const STEPS = [100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700] as const;

export function sequentialStep(value: number, min = 0, max = 1): string {
  const t = max === min ? 0 : Math.min(1, Math.max(0, (value - min) / (max - min)));
  const idx = Math.min(STEPS.length - 1, Math.floor(t * STEPS.length));
  return `var(--seq-${STEPS[idx]})`;
}

// Steps >=450 are dark enough that white text reads better than the page's
// dark-on-light default.
export function sequentialTextColor(value: number, min = 0, max = 1): string {
  const t = max === min ? 0 : Math.min(1, Math.max(0, (value - min) / (max - min)));
  const idx = Math.min(STEPS.length - 1, Math.floor(t * STEPS.length));
  return STEPS[idx] >= 450 ? "#ffffff" : "#0b0b0b";
}
