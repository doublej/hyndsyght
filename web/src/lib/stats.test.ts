import { describe, expect, test } from "bun:test";
import type { DayStats } from "./api";
import { activeBy, punchcard, streak, tracked, weekdayAverages } from "./stats";

function day(date: string, activeHours: number, hour = 9): DayStats {
  const hours = new Array(24).fill(0);
  hours[hour] = activeHours * 60;
  return {
    day: date,
    active_seconds: activeHours * 3600,
    first_ts: null,
    last_ts: null,
    switches: 0,
    break_start: null,
    break_seconds: 0,
    focus_app: null,
    focus_seconds: 0,
    agent_seconds: 0,
    agent_away_seconds: 0,
    hours,
  };
}

describe("streak", () => {
  test("counts back from the last day", () => {
    expect(streak([day("2026-09-21", 0), day("2026-09-22", 2), day("2026-09-23", 3)])).toBe(2);
  });

  test("a short last day does not break the streak", () => {
    expect(streak([day("2026-09-22", 2), day("2026-09-23", 3), day("2026-09-24", 0.2)])).toBe(2);
  });
});

describe("averages skip untracked days", () => {
  // 2026-09-21 and 2026-09-28 are Mondays
  const days = [day("2026-09-21", 4), day("2026-09-28", 2), day("2026-09-22", 0)];

  test("weekday average", () => {
    expect(tracked(days)).toHaveLength(2);
    expect(weekdayAverages(days)[0]).toBe(3 * 3600);
    expect(weekdayAverages(days)[1]).toBe(0);
  });

  test("punchcard averages minutes per weekday hour", () => {
    expect(punchcard(days)[0][9]).toBe(180);
  });
});

describe("activeBy", () => {
  test("counts full hours before the time and the current hour pro rata", () => {
    const d = day("2026-09-21", 2, 9); // 120 minutes in the 09:00 bucket
    expect(activeBy(d, 9 * 60)).toBe(0);
    expect(activeBy(d, 9 * 60 + 30)).toBe(60 * 60);
    expect(activeBy(d, 23 * 60)).toBe(2 * 3600);
  });
});
