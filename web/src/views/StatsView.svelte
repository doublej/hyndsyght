<script lang="ts">
  import { poll } from "../lib/poll.svelte";
  import { buildHash } from "../lib/route";
  import StatCard from "../lib/StatCard.svelte";
  import BarList from "../lib/BarList.svelte";
  import DailyBars from "../lib/DailyBars.svelte";
  import Heatmap from "../lib/Heatmap.svelte";
  import { dayLabel, duration, durationFromMinutes } from "../lib/format";
  import { WEEKDAYS, average, best, punchcard, streak, tracked, weekdayAverages } from "../lib/stats";
  import type { DayStats } from "../lib/api";

  let { params = new URLSearchParams() }: { params?: URLSearchParams } = $props();

  const RANGES = [7, 30, 90];
  const range = $derived(Number(params.get("range")) || 30);
  const stats = poll<DayStats[]>(() => `/api/stats?days=${range}`, 300_000);

  const days = $derived(stats.data ?? []);
  const seen = $derived(tracked(days));
  const avgActive = $derived(average(seen, (d) => d.active_seconds));
  const busiest = $derived(best(seen, (d) => d.active_seconds));
  const focus = $derived(best(seen, (d) => d.focus_seconds));
  const switchRate = $derived.by(() => {
    const hours = seen.reduce((s, d) => s + d.active_seconds, 0) / 3600;
    return hours ? seen.reduce((s, d) => s + d.switches, 0) / hours : 0;
  });
  const awayTotal = $derived(seen.reduce((s, d) => s + d.agent_away_seconds, 0));

  const topFocus = $derived(
    [...seen]
      .sort((a, b) => b.focus_seconds - a.focus_seconds)
      .slice(0, 5)
      .map((d) => ({
        label: `${d.focus_app}, ${dayLabel(d.day)}`,
        value: d.focus_seconds,
        app: d.focus_app ?? undefined,
      })),
  );
</script>

<div class="toolbar">
  {#each RANGES as r (r)}
    <a class="btn" class:active={range === r} href={buildHash("stats", { range: String(r) })}>
      Last {r} days
    </a>
  {/each}
  {#if stats.data && seen.length < days.length}
    <span class="muted">{days.length - seen.length} of {days.length} days have no data</span>
  {/if}
</div>

{#if stats.error}
  <p class="error">{stats.error}</p>
{/if}

{#if stats.data && !seen.length}
  <p class="muted">No activity in this range yet. Leave the daemon running and come back tomorrow.</p>
{:else}
  <div class="readings">
    <StatCard value={stats.data ? duration(avgActive) : "—"} label="average active day" />
    <a class="stat-link" href={busiest ? buildHash("overview", { day: busiest.day }) : undefined}>
      <StatCard
        value={busiest ? duration(busiest.active_seconds) : "—"}
        label="busiest day"
        note={busiest ? dayLabel(busiest.day) : undefined}
      />
    </a>
    <a class="stat-link" href={focus ? buildHash("overview", { day: focus.day }) : undefined}>
      <StatCard
        value={focus ? duration(focus.focus_seconds) : "—"}
        label="longest run in one app"
        note={focus ? `${focus.focus_app}, ${dayLabel(focus.day)}` : undefined}
        app={focus?.focus_app ?? undefined}
      />
    </a>
    <StatCard
      value={stats.data ? `${streak(days)} days` : "—"}
      label="streak of days over 1h active"
    />
    <StatCard value={stats.data ? switchRate.toFixed(0) : "—"} label="app switches per active hour" />
    <StatCard value={stats.data ? duration(awayTotal) : "—"} label="agents worked while you were away" />
  </div>

  <section class="card">
    <h2>Active time per day</h2>
    <DailyBars {days} average={avgActive} />
    <p class="muted small">Click a day to open it. Dates mark Mondays.</p>
  </section>

  <section class="card">
    <h2>When you work</h2>
    <Heatmap values={punchcard(days)} rows={WEEKDAYS} format={(m) => `${durationFromMinutes(m)} active on average`} />
    <p class="muted small">Average active minutes in each hour, over days with data.</p>
  </section>

  <div class="two-col">
    <section class="card">
      <h2>Average by weekday</h2>
      <BarList
        items={weekdayAverages(days).map((s, w) => ({ label: WEEKDAYS[w], value: s }))}
        formatValue={duration}
      />
    </section>
    <section class="card">
      <h2>Longest runs in one app</h2>
      <BarList items={topFocus} formatValue={duration} />
    </section>
  </div>
{/if}
