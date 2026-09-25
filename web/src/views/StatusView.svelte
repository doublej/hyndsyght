<script lang="ts">
  import { poll } from "../lib/poll.svelte";
  import { relativeAge } from "../lib/format";
  import type { StatusReport } from "../lib/api";

  let {}: { params?: URLSearchParams } = $props();

  const status = poll<StatusReport>(() => "/api/status", 30_000);

  function humanSize(bytes: number): string {
    const kb = bytes / 1024;
    return kb < 1024 ? `${kb.toFixed(0)} KB` : `${(kb / 1024).toFixed(1)} MB`;
  }
</script>

{#if status.error}
  <p class="error">{status.error}</p>
{/if}

{#if status.data}
  <div class="grid">
    <div class="card">
      <strong
        >{status.data.daemon_running ? "✓ Daemon running" : "✗ Daemon not running"}</strong
      >
      {#if !status.data.daemon_running}
        <p class="muted">Run <code>just service-install</code> or <code>hyndsyght daemon</code>.</p>
      {/if}
    </div>
    <div class="card">
      <strong>
        {status.data.hooks_registered ? "✓" : "✗"} Hooks {status.data
          .hooks_registered_count[0]}/{status.data.hooks_registered_count[1]}
      </strong>
      {#if !status.data.hooks_registered}
        <p class="muted">Run <code>hyndsyght setup</code>.</p>
      {/if}
    </div>
    <div class="card">
      <strong
        >{status.data.window_titles_empty_last_hour
          ? "✗ Screen Recording permission"
          : "✓ Screen Recording OK"}</strong
      >
      {#if status.data.window_titles_empty_last_hour}
        <p class="muted">
          <a
            href="x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
          >
            Open Privacy &amp; Security → Screen Recording
          </a>
        </p>
      {/if}
    </div>
    <div class="card">
      <strong>Database</strong>
      <p class="muted">{humanSize(status.data.db_size_bytes)}</p>
    </div>
  </div>

  <section class="card">
    <h2>Last event per source</h2>
    {#each Object.entries(status.data.last_event_per_source) as [source, ts] (source)}
      <p>{source}: {relativeAge(ts)}</p>
    {:else}
      <p class="muted">No events recorded yet.</p>
    {/each}
  </section>
{/if}
