<script lang="ts">
  import { poll } from "../lib/poll.svelte";
  import DateRange from "../lib/DateRange.svelte";
  import BarList from "../lib/BarList.svelte";
  import StatCard from "../lib/StatCard.svelte";
  import { duration, durationFromMinutes } from "../lib/format";
  import type { AttentionSummary, TrendPoint } from "../lib/api";

  let {}: { params?: URLSearchParams } = $props();

  let since = $state<number | undefined>(undefined);
  let until = $state<number | undefined>(undefined);
  let source = $state("window");
  let category = $state("");

  const url = $derived.by(() => {
    const query = new URLSearchParams();
    if (since) query.set("since", String(since));
    if (until) query.set("until", String(until));
    if (source) query.set("source", source);
    if (category) query.set("category", category);
    const qs = query.toString();
    return `/api/attention${qs ? `?${qs}` : ""}`;
  });

  const summary = poll<AttentionSummary>(() => url);
  const trend = poll<TrendPoint[]>(() => "/api/trend?metric=attention&days=14");

  const trendItems = $derived(
    (trend.data ?? []).map((d) => ({
      label: d.day.slice(5),
      value: (d.longest_stretch_seconds ?? 0) / 60,
    })),
  );
</script>

<div class="toolbar">
  <select bind:value={source}>
    <option value="window">window</option>
    <option value="agent">agent</option>
  </select>
  <input type="text" placeholder="category" bind:value={category} />
</div>
<DateRange bind:since bind:until />

{#if summary.error}
  <p class="error">{summary.error}</p>
{/if}

{#if summary.data}
  <div class="stats">
    <StatCard value={duration(summary.data.longest_stretch_seconds)} label="longest stretch" />
    <StatCard value={summary.data.switches_per_hour.toFixed(1)} label="switches / hour" />
    <StatCard value={duration(summary.data.median_session_seconds)} label="median session" />
  </div>
{/if}

<section class="card">
  <h2>14-day trend — longest stretch</h2>
  <BarList items={trendItems} vertical formatValue={durationFromMinutes} />
</section>
