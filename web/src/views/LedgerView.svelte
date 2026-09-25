<script lang="ts">
  import { poll } from "../lib/poll.svelte";
  import BarList from "../lib/BarList.svelte";
  import StatCard from "../lib/StatCard.svelte";
  import { durationFromMinutes } from "../lib/format";
  import type { LedgerSummary, TrendPoint } from "../lib/api";

  let {}: { params?: URLSearchParams } = $props();

  const summary = poll<LedgerSummary>(() => "/api/ledger");
  const trend = poll<TrendPoint[]>(() => "/api/trend?metric=ledger&days=14");

  const agentPerHuman = $derived(
    summary.data && summary.data.human_minutes > 0
      ? summary.data.agent_minutes / summary.data.human_minutes
      : 0,
  );

  const trendItems = $derived(
    (trend.data ?? []).map((d) => ({ label: d.day.slice(5), value: d.agent_minutes ?? 0 })),
  );
</script>

{#if summary.error}
  <p class="error">{summary.error}</p>
{/if}

{#if summary.data}
  <div class="stats">
    <StatCard value={durationFromMinutes(summary.data.human_minutes)} label="human time today" />
    <StatCard
      value={durationFromMinutes(summary.data.agent_minutes)}
      label="agent time today (sessions overlap)"
    />
    <StatCard
      value={durationFromMinutes(summary.data.overlap_minutes)}
      label="overlap with human time"
    />
    <StatCard value={`${agentPerHuman.toFixed(1)}×`} label="agent minutes per human minute" />
  </div>
{/if}

<section class="card">
  <h2>14-day trend — agent minutes</h2>
  <BarList items={trendItems} vertical formatValue={durationFromMinutes} />
</section>
