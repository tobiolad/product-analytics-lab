// Fixed order matching generator/constants.py::ACQUISITION_CHANNELS -- categorical
// hue slots are assigned by this order, never re-sorted by value, so a filter
// or a bad month never repaints which channel owns which color.
export const CHANNEL_ORDER = [
  "organic_search",
  "paid_search",
  "referral",
  "content_marketing",
  "social",
  "partner",
] as const;

export const CHANNEL_LABELS: Record<string, string> = {
  organic_search: "Organic search",
  paid_search: "Paid search",
  referral: "Referral",
  content_marketing: "Content marketing",
  social: "Social",
  partner: "Partner",
};

export const CHANNEL_COLORS: Record<string, string> = {
  organic_search: "var(--series-1)",
  paid_search: "var(--series-2)",
  referral: "var(--series-3)",
  content_marketing: "var(--series-4)",
  social: "var(--series-5)",
  partner: "var(--series-6)",
};

export const UNKNOWN_COLOR = "var(--text-muted)";

export function channelLabel(channel: string | null | undefined): string {
  if (!channel) return "Unknown";
  return CHANNEL_LABELS[channel] ?? channel;
}

export function channelColor(channel: string | null | undefined): string {
  if (!channel) return UNKNOWN_COLOR;
  return CHANNEL_COLORS[channel] ?? UNKNOWN_COLOR;
}
