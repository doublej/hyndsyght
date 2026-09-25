<script lang="ts">
  import { poll } from "../lib/poll.svelte";
  import AppIcon from "../lib/AppIcon.svelte";
  import { addRule, apiGet, literalPattern, payloadApp } from "../lib/api";
  import { clockTime } from "../lib/format";
  import type { RawEvent, RulesSummary } from "../lib/api";

  let { params = new URLSearchParams() }: { params?: URLSearchParams } = $props();

  const source = $derived(params.get("source") ?? "");
  const kind = $derived(params.get("kind") ?? "");
  const category = $derived(params.get("category") ?? "");
  const session = $derived(params.get("session") ?? "");
  const q = $derived(params.get("q") ?? "");
  const since = $derived(params.get("since") ?? "");
  const until = $derived(params.get("until") ?? "");

  const baseQuery = $derived.by(() => {
    const query = new URLSearchParams();
    if (source) query.set("source", source);
    if (kind) query.set("kind", kind);
    if (category) query.set("category", category);
    if (session) query.set("session", session);
    if (q) query.set("q", q);
    if (since) query.set("since", since);
    if (until) query.set("until", until);
    return query.toString();
  });

  const eventsUrl = $derived(`/api/events?limit=100${baseQuery ? `&${baseQuery}` : ""}`);
  const live = poll<RawEvent[]>(() => eventsUrl);
  const rules = poll<RulesSummary>(() => "/api/rules", 60_000);
  const categoryNames = $derived((rules.data?.categories ?? []).map((c) => c.name));

  let older = $state<RawEvent[]>([]);
  let loadingOlder = $state(false);
  let expandedId = $state<number | null>(null);

  let assigningId = $state<number | null>(null);
  let addingCategoryFor = $state<number | null>(null);
  let newCategoryName = $state("");
  let assignError = $state<string | null>(null);
  let saving = $state(false);

  function startAssign(event: RawEvent) {
    assigningId = event.id;
    addingCategoryFor = null;
    newCategoryName = "";
    assignError = null;
  }

  function pickCategory(event: RawEvent, value: string) {
    if (value === "__new__") {
      addingCategoryFor = event.id;
      return;
    }
    assign(event, value);
  }

  async function assign(event: RawEvent, category: string) {
    if (!category || !event.title) return;
    saving = true;
    assignError = null;
    try {
      await addRule(category, literalPattern(event.title));
      assigningId = null;
      addingCategoryFor = null;
      await Promise.all([live.refresh(), rules.refresh()]);
    } catch (e) {
      assignError = e instanceof Error ? e.message : String(e);
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    baseQuery; // reset accumulated pagination whenever filters change
    older = [];
  });

  const allEvents = $derived([...(live.data ?? []), ...older]);

  async function loadOlder() {
    const lastId = allEvents.at(-1)?.id;
    if (!lastId) return;
    loadingOlder = true;
    try {
      const prefix = baseQuery ? `${baseQuery}&` : "";
      const page = await apiGet<RawEvent[]>(
        `/api/events?limit=100&${prefix}before_id=${lastId}`,
      );
      older = [...older, ...page];
    } finally {
      loadingOlder = false;
    }
  }

  function updateFilter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    location.hash = `#/events?${next.toString()}`;
  }

  function updateDate(key: "since" | "until", value: string) {
    if (!value) {
      updateFilter(key, "");
      return;
    }
    const ts = new Date(value).getTime() / 1000 + (key === "until" ? 86400 - 1 : 0);
    updateFilter(key, String(ts));
  }

  function toDateInput(unixSeconds: string): string {
    return unixSeconds ? new Date(Number(unixSeconds) * 1000).toISOString().slice(0, 10) : "";
  }
</script>

<div class="toolbar">
  <select
    value={source}
    onchange={(e) => updateFilter("source", (e.target as HTMLSelectElement).value)}
  >
    <option value="">All sources</option>
    <option value="window">window</option>
    <option value="afk">afk</option>
    <option value="agent">agent</option>
  </select>
  <input
    type="text"
    placeholder="kind"
    value={kind}
    onchange={(e) => updateFilter("kind", (e.target as HTMLInputElement).value)}
  />
  <input
    type="text"
    placeholder="category"
    value={category}
    onchange={(e) => updateFilter("category", (e.target as HTMLInputElement).value)}
  />
  <input
    type="text"
    placeholder="search title…"
    value={q}
    onchange={(e) => updateFilter("q", (e.target as HTMLInputElement).value)}
  />
  <input
    type="date"
    value={toDateInput(since)}
    onchange={(e) => updateDate("since", (e.target as HTMLInputElement).value)}
  />
  <input
    type="date"
    value={toDateInput(until)}
    onchange={(e) => updateDate("until", (e.target as HTMLInputElement).value)}
  />
  {#if session}
    <span class="badge">
      session: {session.slice(0, 8)}
      <button class="btn" onclick={() => updateFilter("session", "")}>×</button>
    </span>
  {/if}
</div>

{#if live.error}
  <p class="error">{live.error}</p>
{/if}
{#if assignError}
  <p class="error">{assignError}</p>
{/if}

<table>
  <thead>
    <tr>
      <th>Source</th>
      <th>Kind</th>
      <th>Title</th>
      <th>Category</th>
      <th>Intent</th>
      <th>Start</th>
      <th>End</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    {#each allEvents as event (event.id)}
      <tr>
        <td>{event.source}</td>
        <td>{event.kind}</td>
        <td>
          {#if payloadApp(event)}<AppIcon app={payloadApp(event)!} />{/if}
          {event.title ?? "—"}
        </td>
        <td>
          {#if assigningId === event.id}
            {#if addingCategoryFor === event.id}
              <input
                type="text"
                placeholder="new category…"
                bind:value={newCategoryName}
                disabled={saving}
                onkeydown={(e) => e.key === "Enter" && assign(event, newCategoryName)}
              />
              <button class="btn" disabled={saving} onclick={() => assign(event, newCategoryName)}>
                Save
              </button>
            {:else}
              <select
                disabled={saving}
                onchange={(e) => pickCategory(event, (e.target as HTMLSelectElement).value)}
              >
                <option value="" selected disabled>Choose a category…</option>
                {#each categoryNames as name (name)}
                  <option value={name}>{name}</option>
                {/each}
                <option value="__new__">New category…</option>
              </select>
            {/if}
          {:else}
            <button
              class="badge"
              disabled={!event.title}
              onclick={() => startAssign(event)}
              title={event.title ? "Assign a category" : "No title to match on"}
            >
              {event.category}
            </button>
          {/if}
        </td>
        <td>{event.intent ?? "—"}</td>
        <td>{clockTime(event.ts_start)}</td>
        <td>{event.ts_end ? clockTime(event.ts_end) : "—"}</td>
        <td>
          <button
            class="btn"
            onclick={() => (expandedId = expandedId === event.id ? null : event.id)}
          >
            {expandedId === event.id ? "Hide" : "Details"}
          </button>
        </td>
      </tr>
      {#if expandedId === event.id}
        <tr>
          <td colspan="8"><pre>{event.payload ?? "no payload"}</pre></td>
        </tr>
      {/if}
    {:else}
      <tr>
        <td colspan="8">No events yet.</td>
      </tr>
    {/each}
  </tbody>
</table>

<button class="btn" onclick={loadOlder} disabled={loadingOlder}>
  {loadingOlder ? "Loading…" : "Load older"}
</button>
