<script lang="ts">
  import { poll } from "../lib/poll.svelte";
  import { addRule, apiGet, removeRule } from "../lib/api";
  import { buildHash } from "../lib/route";
  import BarList from "../lib/BarList.svelte";
  import DateRange from "../lib/DateRange.svelte";
  import { duration } from "../lib/format";
  import type { CategorizeResult, CategoryTotal, RulesSummary } from "../lib/api";

  let {}: { params?: URLSearchParams } = $props();

  let since = $state<number | undefined>(undefined);
  let until = $state<number | undefined>(undefined);

  const url = $derived.by(() => {
    const query = new URLSearchParams();
    if (since) query.set("since", String(since));
    if (until) query.set("until", String(until));
    const qs = query.toString();
    return `/api/categories${qs ? `?${qs}` : ""}`;
  });

  const breakdown = poll<CategoryTotal[]>(() => url);
  const rules = poll<RulesSummary>(() => "/api/rules", 60_000);

  const items = $derived(
    (breakdown.data ?? []).map((c) => ({ label: c.category, value: c.seconds })),
  );

  let previewTitle = $state("");
  let previewResult = $state<CategorizeResult | null>(null);

  let newPatternByCategory = $state<Record<string, string>>({});
  let rulesError = $state<string | null>(null);
  let savingPattern = $state<string | null>(null);

  async function addPattern(category: string) {
    const pattern = (newPatternByCategory[category] ?? "").trim();
    if (!pattern) return;
    savingPattern = `${category}:${pattern}`;
    rulesError = null;
    try {
      await addRule(category, pattern);
      newPatternByCategory[category] = "";
      await Promise.all([rules.refresh(), breakdown.refresh()]);
    } catch (e) {
      rulesError = e instanceof Error ? e.message : String(e);
    } finally {
      savingPattern = null;
    }
  }

  async function removePattern(category: string, pattern: string) {
    savingPattern = `${category}:${pattern}`;
    rulesError = null;
    try {
      await removeRule(category, pattern);
      await Promise.all([rules.refresh(), breakdown.refresh()]);
    } catch (e) {
      rulesError = e instanceof Error ? e.message : String(e);
    } finally {
      savingPattern = null;
    }
  }

  $effect(() => {
    const title = previewTitle;
    if (!title) {
      previewResult = null;
      return;
    }
    apiGet<CategorizeResult>(`/api/categorize?title=${encodeURIComponent(title)}`).then(
      (result) => {
        previewResult = result;
      },
    );
  });
</script>

<DateRange bind:since bind:until />

{#if breakdown.error}
  <p class="error">{breakdown.error}</p>
{/if}

<BarList {items} formatValue={duration} />

<div class="grid">
  {#each breakdown.data ?? [] as entry (entry.category)}
    <a class="card" href={buildHash("events", { category: entry.category })}>
      {entry.category} <span class="muted">{duration(entry.seconds)}</span>
    </a>
  {/each}
</div>

<section class="card">
  <h2>Rules preview</h2>
  <input type="text" placeholder="type a window title…" bind:value={previewTitle} />
  {#if previewResult}
    <p>
      {#if previewResult.away}
        <span class="badge">away</span>
      {:else if previewResult.redacted}
        <span class="badge">redacted</span>
      {:else}
        <span class="badge">{previewResult.category}</span>
      {/if}
    </p>
  {/if}
  {#if rulesError}
    <p class="error">{rulesError}</p>
  {/if}
  <details open>
    <summary>All rules</summary>
    {#each rules.data?.categories ?? [] as cat (cat.name)}
      <div class="rule-group">
        <strong>{cat.name}</strong>
        {#each cat.patterns as pattern (pattern)}
          <span class="badge">
            {pattern}
            <button
              class="btn"
              disabled={savingPattern === `${cat.name}:${pattern}`}
              onclick={() => removePattern(cat.name, pattern)}
            >
              ×
            </button>
          </span>
        {/each}
        <input
          type="text"
          placeholder="add pattern…"
          bind:value={newPatternByCategory[cat.name]}
          onkeydown={(e) => e.key === "Enter" && addPattern(cat.name)}
        />
        <button
          class="btn"
          disabled={savingPattern === `${cat.name}:${newPatternByCategory[cat.name] ?? ""}`}
          onclick={() => addPattern(cat.name)}
        >
          Add pattern
        </button>
      </div>
    {/each}
    <p class="muted">redact: {rules.data?.redact_patterns.join(", ") ?? ""}</p>
    <p class="muted">away: {rules.data?.away_patterns.join(", ") ?? ""}</p>
  </details>
</section>
