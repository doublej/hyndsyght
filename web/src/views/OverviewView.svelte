<script lang="ts">
  import { poll } from "../lib/poll.svelte";
  import { buildHash } from "../lib/route";
  import StatCard from "../lib/StatCard.svelte";
  import BarList from "../lib/BarList.svelte";
  import DayRibbon from "../lib/DayRibbon.svelte";
  import { categoryColor } from "../lib/colors";
  import { activeBy, average, tracked } from "../lib/stats";
  import {
    dayLabel,
    duration,
    durationFromMinutes,
    hourMinute,
    isoDay,
    shiftDay,
      } from "../lib/format";
  import type { DayDetail, DayStats, RulesSummary, SessionSummary } from "../lib/api";

  let { params = new URLSearchParams() }: { params?: URLSearchParams } = $props();

  const today = isoDay(new Date());
  const day = $derived(params.get("day") ?? today);
  const isToday = $derived(day === today);

  const detail = poll<DayDetail>(() => `/api/day?day=${day}`);
  const history = poll<DayStats[]>(() => "/api/stats?days=31", 300_000);
  const rules = poll<RulesSummary>(() => "/api/rules", 60_000);
  const sessions = poll<SessionSummary[]>(() => "/api/sessions?limit=3");

  const categoryOrder = $derived((rules.data?.categories ?? []).map((c) => c.name));
  const d = $derived(detail.data?.day === day ? detail.data : null);

  const weekBefore = $derived(
    tracked(history.data ?? []).filter((h) => h.day >= shiftDay(day, -7) && h.day < day),
  );
  // Today is half a day: compare it with the same stretch of the days before, not whole days.
  const now = $derived.by(() => {
    void d; // re-read the clock on every poll
    return new Date();
  });
  const nowMinute = $derived(now.getHours() * 60 + now.getMinutes());
  const activeDelta = $derived(
    d && weekBefore.length
      ? d.active_seconds -
          average(weekBefore, (h) => (isToday ? activeBy(h, nowMinute) : h.active_seconds))
      : null,
  );

  const categoryTotals = $derived.by(() => {
    const totals = new Map<string, number>();
    for (const run of d?.runs ?? []) {
      totals.set(run.category, (totals.get(run.category) ?? 0) + run.end - run.start);
    }
    return [...totals].sort((a, b) => b[1] - a[1]);
  });

  // Active through midnight clips to the next day's 00:00; say 24:00 instead.
  const lastActivity = (ts: number) => (shiftDay(day, 1) === isoDay(new Date(ts * 1000)) ? "24:00" : hourMinute(ts));
  const busiestHour = $derived(
    d?.hours.reduce<[number, number] | null>((top, m, h) => (m > (top?.[1] ?? 0) ? [h, m] : top), null),
  );
  const perActiveHour = (x: number) => (d && d.active_seconds ? x / (d.active_seconds / 3600) : 0);
</script>

<div class="toolbar day-nav">
  <a class="btn" href={buildHash("overview", { day: shiftDay(day, -1) })} aria-label="Previous day">‹</a>
  <span class="day-title">{isToday ? "Today" : dayLabel(day)}</span>
  {#if !isToday}
    <a class="btn" href={buildHash("overview", { day: shiftDay(day, 1) })} aria-label="Next day">›</a>
    <a class="btn" href={buildHash("overview")}>Back to today</a>
  {/if}
</div>

{#if detail.error}
  <p class="error">{detail.error}</p>
{/if}

{#if d?.first_ts && d.last_ts}
  <p class="headline">
    {#if isToday}
      <strong>{duration(d.active_seconds)}</strong> at the computer so far, starting at
      <strong>{hourMinute(d.first_ts)}</strong>.
    {:else}
      <strong>{duration(d.active_seconds)}</strong> at the computer, from
      <strong>{hourMinute(d.first_ts)}</strong> to <strong>{lastActivity(d.last_ts)}</strong>.
    {/if}
  </p>
  <p class="dek">
    {#if activeDelta !== null}
      That is {duration(Math.abs(activeDelta))}
      {activeDelta < 0 ? "less" : "more"} than
      {#if isToday}
        your average by {hourMinute(now.getTime() / 1000)} on the 7 days before.
      {:else}
        your average for the 7 days before.
      {/if}
    {/if}
    {#if d.break_start}
      Your longest break was {duration(d.break_seconds)}, from {hourMinute(d.break_start)}.
    {/if}
  </p>
{:else if d}
  <p class="headline muted">Nothing recorded on this day.</p>
  <p class="dek">The daemon records while it runs. Pick another day with the arrows.</p>
{/if}

{#if d && d.runs.length}
  <section class="card">
    <DayRibbon
      runs={d.runs}
      agents={d.agents}
      dayStart={new Date(`${day}T00:00:00`).getTime() / 1000}
      categories={categoryOrder}
    />
    <div class="legend">
      {#each categoryTotals as [category, seconds] (category)}
        <a class="legend-item" href={buildHash("categories")}>
          <span class="swatch" style="background: {categoryColor(category, categoryOrder)}"></span>
          {category} <span class="muted">{duration(seconds)}</span>
        </a>
      {/each}
      <span class="legend-item"><span class="swatch hatch"></span>agents running</span>
    </div>
    <p class="muted small">
      Each block is 5 minutes, coloured by its main category. Click a block to see its events.
    </p>
  </section>

  <div class="readings">
    <StatCard value={duration(d.focus_seconds)} label="longest run in one app" note={d.focus_app ?? undefined} app={d.focus_app ?? undefined} />
    <StatCard value={perActiveHour(d.switches).toFixed(0)} label="app switches per active hour" />
    <StatCard
      value={busiestHour ? `${String(busiestHour[0]).padStart(2, "0")}:00` : "—"}
      label="busiest hour"
      note={busiestHour ? `${durationFromMinutes(busiestHour[1])} active` : undefined}
    />
    <StatCard
      value={duration(d.agent_away_seconds)}
      label="agents worked while you were away"
      note={`${duration(d.agent_seconds)} with any agent running`}
    />
  </div>
{/if}

<div class="two-col">
  <section class="card">
    <h2>Apps</h2>
    <BarList
      items={(d?.apps ?? []).slice(0, 8).map((a) => ({ label: a.app, value: a.seconds, app: a.app }))}
      formatValue={duration}
    />
  </section>
  <section class="card">
    <h2>Active minutes per hour</h2>
    <BarList
      items={(d?.hours ?? []).map((m, h) => ({ label: String(h).padStart(2, "0"), value: m }))}
      vertical
      formatValue={durationFromMinutes}
    />
  </section>
</div>

{#if isToday}
  <section class="card">
    <h2>Recent agent activity</h2>
    <ul class="intents">
      {#each sessions.data ?? [] as session (session.session_id)}
        <li>
          <a href={buildHash("events", { session: session.session_id })}>{session.session_id.slice(0, 8)}</a>
          <span class:muted={!session.last_intent} title={session.last_intent ?? undefined}>
            {session.last_intent ?? "No intent captured"}
          </span>
        </li>
      {:else}
        <li class="muted">No agent activity yet.</li>
      {/each}
    </ul>
  </section>
{/if}
