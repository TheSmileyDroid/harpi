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
