// Dev (`bun run dev`, Vite's own server) reads the token from
// VITE_API_TOKEN, written by a pre-dev step. Production reads it from
// window.__HYNDSYGHT_TOKEN__, injected server-side into index.html.
declare global {
  interface Window {
    __HYNDSYGHT_TOKEN__?: string;
  }
}

const token = import.meta.env.DEV ? import.meta.env.VITE_API_TOKEN : window.__HYNDSYGHT_TOKEN__;

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

/** The app behind a window or media event, from its payload. */
export function payloadApp(event: RawEvent): string | undefined {
  if (event.source !== "window" && event.source !== "media") return undefined;
  return event.payload ? JSON.parse(event.payload).app : undefined;
}

const icons = new Map<string, Promise<string | null>>();

/** An app's icon as an object URL, fetched once per page load; null when there is none. */
export function appIcon(app: string): Promise<string | null> {
  if (!icons.has(app)) {
    const path = `/api/app-icon?app=${encodeURIComponent(app)}`;
    const url = fetch(path, { headers: { Authorization: `Bearer ${token}` } }).then(async (res) =>
      res.ok ? URL.createObjectURL(await res.blob()) : null,
    );
    icons.set(app, url);
  }
  return icons.get(app)!;
}

async function apiSend<T>(method: "POST" | "DELETE", path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `${path} -> ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function addRule(category: string, pattern: string): Promise<RulesSummary> {
  return apiSend<RulesSummary>("POST", "/api/rules", { category, pattern });
}

export function removeRule(category: string, pattern: string): Promise<RulesSummary> {
  return apiSend<RulesSummary>("DELETE", "/api/rules", { category, pattern });
}

/** Escape an app/window title into a literal, word-bounded pattern for /api/rules. */
export function literalPattern(value: string): string {
  return `\\b${value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`;
}

export interface RawEvent {
  id: number;
  event_uid: string | null;
  source: string;
  kind: string;
  title: string | null;
  ts_start: number;
  ts_end: number | null;
  payload: string | null;
  category: string;
  session_id: string | null;
  intent: string | null;
}

export interface AttentionSummary {
  longest_stretch_seconds: number;
  switches_per_hour: number;
  median_session_seconds: number;
}

export interface LedgerSummary {
  human_minutes: number;
  agent_minutes: number;
  overlap_minutes: number;
}

export interface TrendPoint extends Partial<AttentionSummary>, Partial<LedgerSummary> {
  day: string;
}

export interface CategoryTotal {
  category: string;
  seconds: number;
}

export interface RuleCategory {
  name: string;
  patterns: string[];
}

export interface RulesSummary {
  categories: RuleCategory[];
  redact_patterns: string[];
  away_patterns: string[];
}

export interface CategorizeResult {
  away: boolean;
  redacted: boolean;
  category: string | null;
}

export interface SessionSummary {
  session_id: string;
  turns: number;
  subagents: number;
  agent_minutes: number;
  last_intent: string | null;
  last_ts: number;
}

export interface StatusReport {
  daemon_running: boolean;
  db_size_bytes: number;
  last_event_per_source: Record<string, number>;
  hooks_registered: boolean;
  hooks_registered_count: [number, number];
  window_titles_empty_last_hour: boolean;
}

export interface DayStats {
  day: string;
  active_seconds: number;
  first_ts: number | null;
  last_ts: number | null;
  switches: number;
  break_start: number | null;
  break_seconds: number;
  focus_app: string | null;
  focus_seconds: number;
  agent_seconds: number;
  agent_away_seconds: number;
  hours: number[];
}

export interface AppRun {
  app: string;
  category: string;
  title: string | null;
  start: number;
  end: number;
}

export interface DayDetail extends DayStats {
  runs: AppRun[];
  agents: [number, number][];
  apps: { app: string; seconds: number }[];
}
