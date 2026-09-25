<script lang="ts">
  import { apiGet, importAwBucket, removeAwImport } from "../lib/api";
  import type { AwBucket, AwBucketResult, AwOverview } from "../lib/api";
  import { buildHash } from "../lib/route";
  import { isoDay } from "../lib/format";

  let {}: { params?: URLSearchParams } = $props();

  // One request per bucket: the server imports it and answers, so progress is
  // simply how many buckets have answered.
  type Step = "connect" | "choose" | "import" | "done";
  type BucketState = "waiting" | "running" | "failed" | AwBucketResult;
  interface Computer {
    host: string;
    buckets: AwBucket[];
    first: number | null;
    last: number | null;
    importedRows: number;
  }

  const STEPS: { id: Step; label: string }[] = [
    { id: "connect", label: "Connect" },
    { id: "choose", label: "Choose" },
    { id: "import", label: "Import" },
    { id: "done", label: "Done" },
  ];

  let step = $state<Step>("connect");
  let url = $state("http://localhost:5600");
  let overview = $state<AwOverview | null>(null);
  let error = $state<string | null>(null);
  let busy = $state(false);
  let chosen = $state<string[]>([]);
  let progress = $state<Record<string, BucketState>>({});
  let confirmingRemove = $state(false);
  let removed = $state<number | null>(null);

  const stepIndex = $derived(STEPS.findIndex((s) => s.id === step));
  const computers = $derived(byComputer(overview?.buckets ?? [], overview?.until ?? null));
  const queue = $derived((overview?.buckets ?? []).filter((b) => chosen.includes(b.host ?? "")));
  const results = $derived(
    Object.values(progress).filter((p): p is AwBucketResult => typeof p === "object"),
  );
  const answered = $derived(Object.values(progress).filter((p) => p !== "waiting" && p !== "running").length);
  const importedRows = $derived(results.reduce((sum, r) => sum + r.rows, 0));
  const hiddenTitles = $derived(results.reduce((sum, r) => sum + r.hidden, 0));
  const failed = $derived(Object.values(progress).filter((p) => p === "failed").length);

  function byComputer(buckets: AwBucket[], until: number | null): Computer[] {
    const hosts = [...new Set(buckets.map((b) => b.host ?? ""))];
    return hosts.map((host) => {
      const own = buckets.filter((b) => (b.host ?? "") === host);
      const firsts = own.map((b) => b.first).filter((t): t is number => t !== null);
      const lasts = own.map((b) => b.last).filter((t): t is number => t !== null);
      const last = lasts.length ? Math.max(...lasts) : null;
      return {
        host,
        buckets: own,
        first: firsts.length ? Math.min(...firsts) : null,
        last: last !== null && until !== null ? Math.min(last, until) : last,
        importedRows: own.reduce((sum, b) => sum + b.imported_rows, 0),
      };
    });
  }

  function day(ts: number | null): string {
    return ts === null ? "–" : isoDay(new Date(ts * 1000));
  }

  async function connect() {
    busy = true;
    error = null;
    try {
      overview = await apiGet<AwOverview>(`/api/import/activitywatch?url=${encodeURIComponent(url)}`);
      chosen = [...new Set(overview.buckets.map((b) => b.host ?? ""))];
      step = "choose";
    } catch {
      error = `Couldn't reach ActivityWatch at ${url}.`;
    } finally {
      busy = false;
    }
  }

  async function runImport() {
    progress = Object.fromEntries(queue.map((b) => [b.id, "waiting"]));
    removed = null;
    step = "import";
    for (const bucket of queue) {
      progress[bucket.id] = "running";
      try {
        progress[bucket.id] = await importAwBucket(url, bucket.id);
      } catch (e) {
        progress[bucket.id] = "failed";
        error = (e as Error).message;
      }
    }
    step = "done";
  }

  async function removeImported() {
    busy = true;
    try {
      removed = (await removeAwImport()).removed;
      confirmingRemove = false;
    } finally {
      busy = false;
    }
    await connect();
  }

  function toggle(host: string) {
    chosen = chosen.includes(host) ? chosen.filter((h) => h !== host) : [...chosen, host];
  }

  function plural(n: number, one: string, many: string): string {
    return `${n.toLocaleString()} ${n === 1 ? one : many}`;
  }
</script>

<section class="card wizard">
  <h2>Import from ActivityWatch</h2>
  <ol class="steps">
    {#each STEPS as s, i (s.id)}
      <li class:active={i === stepIndex} class:passed={i < stepIndex}>
        <span class="step-num">{i < stepIndex ? "✓" : i + 1}</span>{s.label}
      </li>
    {/each}
  </ol>

  {#if step === "connect"}
    <p class="lead">
      Bring in the window and away history ActivityWatch recorded, so your charts reach back
      before the day hyndsyght started. It all stays on this computer.
    </p>
    <form
      class="toolbar"
      onsubmit={(e) => {
        e.preventDefault();
        connect();
      }}
    >
      <label for="aw-url">ActivityWatch address</label>
      <input id="aw-url" type="text" bind:value={url} />
      <button class="btn active" disabled={busy}>{busy ? "Looking…" : "Look for ActivityWatch"}</button>
    </form>
    {#if error}
      <p class="error">{error}</p>
      <p class="muted">
        Start ActivityWatch and try again. To import an export file instead, run
        <code>hyndsyght import activitywatch --file export.json</code>.
      </p>
    {/if}
  {:else if step === "choose" && overview}
    {#if removed !== null}
      <p class="muted">Removed {plural(removed, "imported row", "imported rows")}.</p>
    {/if}
    {#if overview.until}
      <p class="lead">
        hyndsyght started recording on <strong>{day(overview.until)}</strong>. The import stops
        there, so no minute is counted twice.
      </p>
    {/if}
    {#if computers.length}
      <table>
        <thead>
          <tr><th></th><th>Computer</th><th>History</th><th>Imported before</th></tr>
        </thead>
        <tbody>
          {#each computers as computer (computer.host)}
            <tr>
              <td>
                <input
                  type="checkbox"
                  aria-label="Import {computer.host}"
                  checked={chosen.includes(computer.host)}
                  onchange={() => toggle(computer.host)}
                />
              </td>
              <td>{computer.host || "unknown"}</td>
              <td>{day(computer.first)} to {day(computer.last)}</td>
              <td class="muted">{computer.importedRows ? plural(computer.importedRows, "row", "rows") : "–"}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {:else}
      <p class="error">ActivityWatch has no window or away history here.</p>
    {/if}
    {#if overview.skipped.length}
      <details>
        <summary class="muted">
          {plural(overview.skipped.length, "other bucket is", "other buckets are")} skipped. Editor,
          Screen Time and other watchers don't record the front window.
        </summary>
        <p class="muted small">{overview.skipped.join(", ")}</p>
      </details>
    {/if}
    <p class="muted">
      Titles on your hidden list are left out. Lock-screen time counts as away. Importing again
      replaces the earlier import.
    </p>
    <div class="toolbar">
      <button class="btn active" disabled={!queue.length} onclick={runImport}>
        Import {plural(chosen.length, "computer", "computers")}
      </button>
      <button class="btn" onclick={() => (step = "connect")}>Back</button>
    </div>
    {#if overview.imported_rows}
      {@render removeControls(overview.imported_rows)}
    {/if}
  {:else}
    <p class="lead">
      {answered} of {plural(queue.length, "bucket", "buckets")}
      {step === "done" ? "done" : "imported so far"}
    </p>
    <progress max={queue.length} value={answered}></progress>
    <table>
      <thead>
        <tr><th>Bucket</th><th>Rows</th><th>From</th><th>To</th></tr>
      </thead>
      <tbody>
        {#each queue as bucket (bucket.id)}
          {@const state = progress[bucket.id]}
          <tr>
            <td>{bucket.id}</td>
            {#if typeof state === "object"}
              <td>{state.rows.toLocaleString()}</td>
              <td>{day(state.first)}</td>
              <td>{day(state.last)}</td>
            {:else}
              <td class:error={state === "failed"} colspan="3">
                {state === "running" ? "Importing…" : state === "failed" ? "Failed" : "Waiting"}
              </td>
            {/if}
          </tr>
        {/each}
      </tbody>
    </table>
    {#if step === "done"}
      <p class="lead">
        Imported {plural(importedRows, "row", "rows")}.
        {#if hiddenTitles}{plural(hiddenTitles, "title was", "titles were")} on your hidden list and left out.{/if}
      </p>
      {#if failed && error}<p class="error">{error}</p>{/if}
      <div class="toolbar">
        <a class="btn active" href={buildHash("stats", { range: "366" })}>See the last year in Stats</a>
        <button class="btn" onclick={connect}>Back to the list</button>
      </div>
      {#if importedRows}
        {@render removeControls(importedRows)}
      {/if}
    {/if}
  {/if}
</section>

{#snippet removeControls(rows: number)}
  <div class="toolbar remove">
    {#if confirmingRemove}
      <span>Remove {plural(rows, "imported row", "imported rows")}? Your own recording stays.</span>
      <button class="btn" disabled={busy} onclick={removeImported}>Remove</button>
      <button class="btn" onclick={() => (confirmingRemove = false)}>Cancel</button>
    {:else}
      <button class="btn" onclick={() => (confirmingRemove = true)}>Remove imported history</button>
    {/if}
  </div>
{/snippet}

<style>
  .wizard {
    max-width: 52rem;
  }

  .lead {
    max-width: 44rem;
    margin-bottom: 1rem;
  }

  .steps {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem 1.5rem;
    list-style: none;
    padding: 0;
    margin: 0 0 1.5rem;
    color: var(--muted);
    font-size: var(--step--1);
  }

  .steps li {
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }

  .steps li.active {
    color: var(--ink);
    font-weight: 650;
  }

  .step-num {
    display: inline-grid;
    place-items: center;
    width: 1.5rem;
    height: 1.5rem;
    border: 1px solid currentColor;
    border-radius: 50%;
    font-size: var(--step--2);
  }

  .steps li.active .step-num {
    background: var(--ink);
    border-color: var(--ink);
    color: var(--paper);
  }

  .steps li.passed .step-num {
    border-color: var(--accent);
    color: var(--accent);
  }

  label {
    font-size: var(--step--1);
  }

  #aw-url {
    min-width: 16rem;
  }

  table {
    margin-bottom: 1rem;
  }

  details {
    margin-bottom: 0.75rem;
  }

  summary {
    cursor: pointer;
  }

  progress {
    width: 100%;
    height: 0.5rem;
    margin-bottom: 1rem;
    accent-color: var(--accent);
  }

  .remove {
    border-top: 1px solid var(--rule);
    padding-top: 1rem;
  }
</style>
