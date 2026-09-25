<script lang="ts">
  import AppIcon from "./AppIcon.svelte";

  let {
    items,
    vertical = false,
    formatValue = (v: number) => v.toFixed(0),
  }: {
    items: { label: string; value: number; app?: string }[];
    vertical?: boolean;
    formatValue?: (v: number) => string;
  } = $props();

  const max = $derived(Math.max(1, ...items.map((i) => i.value)));
</script>

{#if vertical}
  <div class="bar-columns">
    {#each items as item (item.label)}
      <div class="bar-col" title="{item.label}: {formatValue(item.value)}">
        <div class="bar-col-fill" style="height: {(item.value / max) * 100}%"></div>
        <span class="bar-col-label">{item.label}</span>
      </div>
    {/each}
  </div>
{:else if items.length === 0}
  <p class="muted">No data.</p>
{:else}
  <div class="bar-list">
    {#each items as item (item.label)}
      <div class="bar-row">
        <span class="bar-label">
          {#if item.app}<AppIcon app={item.app} />{/if}
          {item.label}
        </span>
        <div class="bar-track">
          <div class="bar" style="width: {(item.value / max) * 100}%"></div>
        </div>
        <span class="bar-value">{formatValue(item.value)}</span>
      </div>
    {/each}
  </div>
{/if}
