<script lang="ts">
  import AppIcon from "./AppIcon.svelte";

  let { value, label, note, app }: { value: string; label: string; note?: string; app?: string } =
    $props();
</script>

<div class="stat">
  <span class="stat-value">{value}</span>
  <span class="stat-label">{label}</span>
  {#if note}<span class="stat-note">{#if app}<AppIcon {app} />{/if}{note}</span>{/if}
</div>
