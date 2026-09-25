<script lang="ts">
  let {
    values,
    rows,
    format,
  }: { values: number[][]; rows: string[]; format: (v: number) => string } = $props();

  const max = $derived(Math.max(1, ...values.flat()));
  const HOURS = Array.from({ length: 24 }, (_, h) => h);
</script>

<div class="heatmap">
  {#each values as row, r (rows[r])}
    <span class="heat-label">{rows[r]}</span>
    {#each row as value, h (h)}
      <div
        class="heat-cell"
        style="background: color-mix(in oklab, var(--accent) {(value / max) * 100}%, var(--surface))"
        title="{rows[r]} {String(h).padStart(2, '0')}:00, {format(value)}"
      ></div>
    {/each}
  {/each}
  <span></span>
  {#each HOURS as h (h)}
    <span class="heat-label">{h % 3 === 0 ? String(h).padStart(2, "0") : ""}</span>
  {/each}
</div>
