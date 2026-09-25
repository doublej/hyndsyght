<script lang="ts">
  import { appIcon } from "./api";

  let { app }: { app: string } = $props();
</script>

<!-- The placeholder keeps labels aligned while the icon loads or when there is none. -->
<span class="app-icon" aria-hidden="true">
  {#await appIcon(app) then src}
    {#if src}<img {src} alt="" />{/if}
  {/await}
</span>
