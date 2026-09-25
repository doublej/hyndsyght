<script lang="ts">
  import { poll } from "../lib/poll.svelte";
  import { apiGet } from "../lib/api";
  import { buildHash } from "../lib/route";
  import { durationFromMinutes, relativeAge } from "../lib/format";
  import type { RawEvent, SessionSummary } from "../lib/api";

  let {}: { params?: URLSearchParams } = $props();

  const sessions = poll<SessionSummary[]>(() => "/api/sessions");

  let expanded = $state<string | null>(null);
  let trail = $state<RawEvent[]>([]);
  let loadingTrail = $state(false);

  async function toggle(sessionId: string) {
    if (expanded === sessionId) {
      expanded = null;
      return;
    }
    expanded = sessionId;
    loadingTrail = true;
    try {
      trail = await apiGet<RawEvent[]>(
        `/api/events?session=${encodeURIComponent(sessionId)}&limit=100`,
      );
    } finally {
      loadingTrail = false;
    }
  }
</script>

{#if sessions.error}
  <p class="error">{sessions.error}</p>
{/if}

<table>
  <thead>
    <tr>
      <th>Session</th>
      <th>Turns</th>
      <th>Subagents</th>
      <th>Agent time</th>
      <th>Last intent</th>
      <th>Last active</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    {#each sessions.data ?? [] as session (session.session_id)}
      <tr>
        <td>{session.session_id.slice(0, 12)}</td>
        <td>{session.turns}</td>
        <td>{session.subagents}</td>
        <td>{durationFromMinutes(session.agent_minutes)}</td>
        <td>{session.last_intent ?? "—"}</td>
        <td>{relativeAge(session.last_ts)}</td>
        <td>
          <button class="btn" onclick={() => toggle(session.session_id)}>
            {expanded === session.session_id ? "Hide" : "Trail"}
          </button>
          <a href={buildHash("events", { session: session.session_id })}>Events</a>
        </td>
      </tr>
      {#if expanded === session.session_id}
        <tr>
          <td colspan="7">
            {#if loadingTrail}
              <p class="muted">Loading…</p>
            {:else}
              {#each trail.slice().reverse() as event (event.id)}
                <p class="muted">{event.kind} — {event.intent ?? "in progress"}</p>
              {/each}
            {/if}
          </td>
        </tr>
      {/if}
    {:else}
      <tr>
        <td colspan="7">No agent sessions yet.</td>
      </tr>
    {/each}
  </tbody>
</table>
