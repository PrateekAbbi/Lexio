export function initialsFromEmail(email = "") {
  const name = email.split("@")[0] || "U";
  return name
    .split(/[._-]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function relativeTime(value) {
  if (!value) return "just now";
  const delta = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.round(delta / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.round(hours / 24);
  return days === 1 ? "yesterday" : `${days}d ago`;
}

export function messageCountLabel(count) {
  if (count === null || count === undefined) return "messages";
  return `${count} messages`;
}

export function stripPdfExtension(filename = "") {
  return filename.replace(/\.pdf$/i, "");
}

export function formatMs(value) {
  if (!Number.isFinite(value)) return "--";
  return `${Math.round(value)} ms`;
}

export function formatPercent(value) {
  if (!Number.isFinite(value)) return "--";
  return `${Math.round(value * 100)}%`;
}

export function sourcePercent(source) {
  return formatPercent(source?.similarity_score);
}

export function latencyStatus(value) {
  if (!Number.isFinite(value)) return "neutral";
  if (value < 3000) return "good";
  if (value < 6000) return "warn";
  return "bad";
}
