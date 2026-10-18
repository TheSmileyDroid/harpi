export function formatDuration(seconds: number | null | undefined): string {
  const total = Math.floor(Number(seconds));
  if (!Number.isFinite(total) || total <= 0) return "0:00";
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  const pad = (value: number) => String(value).padStart(2, "0");
  return hours > 0
    ? `${hours}:${pad(minutes)}:${pad(secs)}`
    : `${minutes}:${pad(secs)}`;
}

export function formatVolume(gain: number | null | undefined): string {
  const value = Number(gain);
  if (!Number.isFinite(value)) return "0%";
  const clamped = Math.min(Math.max(value, 0), 1);
  return `${Math.round(clamped * 100)}%`;
}

export function formatSeen(
  seconds: number | null | undefined,
  nowMs = Date.now(),
): string {
  const stamp = Number(seconds);
  if (!Number.isFinite(stamp) || stamp <= 0) return "unknown";
  const age = Math.max(0, Math.floor(nowMs / 1000 - stamp));
  if (age < 10) return "now";
  if (age < 60) return `${age}s ago`;
  return `${Math.floor(age / 60)}m ago`;
}
