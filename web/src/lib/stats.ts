import type { DayStats } from "./api";
import { parseDay } from "./format";

export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** Days the tracker actually saw you; empty days are gaps in the data, not days off. */
export function tracked(days: DayStats[]): DayStats[] {
  return days.filter((d) => d.active_seconds > 0);
}

export function average(days: DayStats[], pick: (d: DayStats) => number): number {
  return days.length ? days.reduce((sum, d) => sum + pick(d), 0) / days.length : 0;
}

/** Active seconds before `minuteOfDay`, from the day's minutes per hour.
 *  ponytail: the current hour counts pro rata; per-minute data if that misleads. */
export function activeBy(day: DayStats, minuteOfDay: number): number {
  const hour = Math.floor(minuteOfDay / 60);
  const before = day.hours.slice(0, hour).reduce((sum, m) => sum + m, 0);
  return (before + (day.hours[hour] ?? 0) * ((minuteOfDay % 60) / 60)) * 60;
}

export function best(days: DayStats[], pick: (d: DayStats) => number): DayStats | undefined {
  return days.reduce<DayStats | undefined>((top, d) => (!top || pick(d) > pick(top) ? d : top), undefined);
}

export function weekdayIndex(day: string): number {
  return (parseDay(day).getDay() + 6) % 7; // Monday first
}

/** Consecutive days with at least `minSeconds` active, counted back from the last day.
 *  The last day is still in progress, so falling short there does not break the streak. */
export function streak(days: DayStats[], minSeconds = 3600): number {
  let count = 0;
  for (let i = days.length - 1; i >= 0; i--) {
    if (days[i].active_seconds >= minSeconds) count++;
    else if (i < days.length - 1) break;
  }
  return count;
}

/** Average active minutes per weekday × hour, over tracked days only. */
export function punchcard(days: DayStats[]): number[][] {
  const sums = WEEKDAYS.map(() => new Array(24).fill(0));
  const counts = new Array(7).fill(0);
  for (const d of tracked(days)) {
    const w = weekdayIndex(d.day);
    counts[w]++;
    d.hours.forEach((minutes, h) => (sums[w][h] += minutes));
  }
  return sums.map((row, w) => row.map((m) => (counts[w] ? m / counts[w] : 0)));
}

export function weekdayAverages(days: DayStats[]): number[] {
  return WEEKDAYS.map((_, w) =>
    average(tracked(days).filter((d) => weekdayIndex(d.day) === w), (d) => d.active_seconds),
  );
}
