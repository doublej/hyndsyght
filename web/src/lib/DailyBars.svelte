<script lang="ts">
  import type { DayStats } from "./api";
  import { buildHash } from "./route";
  import { dayLabel, duration, parseDay } from "./format";

  let { days, average }: { days: DayStats[]; average: number } = $props();

  const max = $derived(Math.max(1, ...days.map((d) => d.active_seconds)));
</script>

<div class="daily">
  <div class="daily-bars">
    {#each days as d (d.day)}
      <a
        class="daily-col"
        href={buildHash("overview", { day: d.day })}
        title="{dayLabel(d.day)}: {d.active_seconds ? duration(d.active_seconds) : 'no data'}"
      >
        <div class="daily-fill" style="height: {(d.active_seconds / max) * 100}%"></div>
      </a>
    {/each}
    {#if average > 0}
      <div class="daily-avg" style="bottom: {(average / max) * 100}%">
        <span>avg {duration(average)}</span>
      </div>
    {/if}
  </div>
  <div class="daily-labels">
    {#each days as d (d.day)}
      <span>{parseDay(d.day).getDay() === 1 ? parseDay(d.day).getDate() : ""}</span>
    {/each}
  </div>
</div>
