<script lang="ts">
  import type { AppRun } from "./api";
  import { buildHash } from "./route";
  import { categoryColor } from "./colors";
  import { duration, hourMinute } from "./format";

  let {
    runs,
    agents,
    dayStart,
    categories,
  }: { runs: AppRun[]; agents: [number, number][]; dayStart: number; categories: string[] } =
    $props();

  const SLOT = 300; // 5 minutes: fine enough to see a coffee break, coarse enough to read
  const DAY = 86400;
  const TICKS = [0, 3, 6, 9, 12, 15, 18, 21];
  const HOURS = Array.from({ length: 23 }, (_, i) => i + 1);

  interface Slot {
    start: number;
    seconds: number;
    category: string;
    apps: [string, number][];
  }

  const slots = $derived.by(() => {
    const byCategory = new Map<number, Map<string, number>>();
    const byApp = new Map<number, Map<string, number>>();
    for (const run of runs) {
      for (let t = run.start; t < run.end; ) {
        const i = Math.floor((t - dayStart) / SLOT);
        const next = Math.min(run.end, dayStart + (i + 1) * SLOT);
        add(byCategory, i, run.category, next - t);
        add(byApp, i, run.app, next - t);
        t = next;
      }
    }
    return [...byCategory].map(([i, cats]): Slot => {
      const apps = [...byApp.get(i)!].sort((a, b) => b[1] - a[1]);
      const top = [...cats].sort((a, b) => b[1] - a[1])[0][0];
      const seconds = apps.reduce((sum, [, s]) => sum + s, 0);
      return { start: dayStart + i * SLOT, seconds, category: top, apps };
    });
  });

  function add(map: Map<number, Map<string, number>>, i: number, key: string, s: number) {
    const inner = map.get(i) ?? new Map<string, number>();
    inner.set(key, (inner.get(key) ?? 0) + s);
    map.set(i, inner);
  }

  const pct = (ts: number) => ((ts - dayStart) / DAY) * 100;
  const now = Date.now() / 1000;

  function slotTitle(slot: Slot): string {
    const apps = slot.apps.map(([app, s]) => `${app} ${duration(s)}`).join(", ");
    return `${hourMinute(slot.start)}, ${slot.category}\n${apps}`;
  }
</script>

{#key dayStart}
<div class="ribbon">
  <span class="lane-label">You</span>
  <div class="lane-track">
    {#each HOURS as h (h)}
      <span class="hour-line" class:major={h % 6 === 0} style="left: {(h / 24) * 100}%"></span>
    {/each}
    {#each slots as slot (slot.start)}
      <a
        class="slot"
        href={buildHash("events", {
          source: "window",
          since: String(slot.start),
          until: String(slot.start + SLOT),
        })}
        style="left: {pct(slot.start)}%; width: {(SLOT / DAY) * 100}%;
          background: {categoryColor(slot.category, categories)};
          opacity: {0.35 + 0.65 * (slot.seconds / SLOT)}"
        title={slotTitle(slot)}
      ></a>
    {/each}
    {#if now < dayStart + DAY}<div class="now" style="left: {pct(now)}%" title="Now"></div>{/if}
  </div>

  <span class="lane-label">Agents</span>
  <div class="lane-track agents">
    {#each HOURS as h (h)}
      <span class="hour-line" class:major={h % 6 === 0} style="left: {(h / 24) * 100}%"></span>
    {/each}
    {#each agents as [start, end] (start)}
      <div
        class="span"
        style="left: {pct(start)}%; width: {Math.max(pct(end) - pct(start), 0.1)}%"
        title="Agents running {hourMinute(start)}–{hourMinute(end)}, {duration(end - start)}"
      ></div>
    {/each}
    {#if now < dayStart + DAY}<div class="now" style="left: {pct(now)}%"></div>{/if}
  </div>

  <span></span>
  <div class="ticks">
    {#each TICKS as hour (hour)}
      <span style="left: {(hour / 24) * 100}%">{String(hour).padStart(2, "0")}</span>
    {/each}
  </div>
</div>
{/key}
