/** Human duration from a minute count: `4h 21m`, `12m`, or `41s` under a minute. */
export function durationFromMinutes(totalMinutes: number): string {
  if (totalMinutes < 1) return `${Math.round(totalMinutes * 60)}s`;
  const rounded = Math.round(totalMinutes);
  const h = Math.floor(rounded / 60);
  const m = rounded % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

/** Human duration from a second count. */
export function duration(seconds: number): string {
  return durationFromMinutes(seconds / 60);
}

export function clockTime(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toLocaleTimeString();
}

export function relativeAge(unixSeconds: number): string {
  const diff = Date.now() / 1000 - unixSeconds;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  return `${Math.round(diff / 3600)}h ago`;
}

export function hourMinute(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Local `YYYY-MM-DD`; toISOString would give the UTC date. */
export function isoDay(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** Noon, so adding days never lands on the wrong side of a DST change. */
export function parseDay(day: string): Date {
  return new Date(`${day}T12:00:00`);
}

export function shiftDay(day: string, days: number): string {
  const date = parseDay(day);
  date.setDate(date.getDate() + days);
  return isoDay(date);
}

export function dayLabel(day: string): string {
  return parseDay(day).toLocaleDateString([], {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}
