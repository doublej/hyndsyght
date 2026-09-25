<script lang="ts">
  import { buildHash, parseHash, type Route } from "./lib/route";
  import { poll } from "./lib/poll.svelte";
  import type { StatusReport } from "./lib/api";
  import OverviewView from "./views/OverviewView.svelte";
  import StatsView from "./views/StatsView.svelte";
  import EventsView from "./views/EventsView.svelte";
  import CategoriesView from "./views/CategoriesView.svelte";
  import AgentsView from "./views/AgentsView.svelte";
  import AttentionView from "./views/AttentionView.svelte";
  import LedgerView from "./views/LedgerView.svelte";
  import StatusView from "./views/StatusView.svelte";
  import ImportView from "./views/ImportView.svelte";

  const VIEWS = [
    { id: "overview", label: "Today", component: OverviewView },
    { id: "stats", label: "Stats", component: StatsView },
    { id: "events", label: "Timeline", component: EventsView },
    { id: "categories", label: "Categories", component: CategoriesView },
    { id: "agents", label: "Claude sessions", component: AgentsView },
    { id: "attention", label: "Focus", component: AttentionView },
    { id: "ledger", label: "Human vs agent", component: LedgerView },
    { id: "status", label: "Status", component: StatusView },
  ] as const;
  // Reachable by address and from Status, but not a tab: you use it once.
  const OTHER_VIEWS = [{ id: "import", label: "Import", component: ImportView }] as const;

  let route = $state<Route>(parseHash(location.hash));

  function onHashChange() {
    route = parseHash(location.hash);
  }

  $effect(() => {
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  });

  const status = poll<StatusReport>(() => "/api/status", 30_000);

  const active = $derived(
    [...VIEWS, ...OTHER_VIEWS].find((v) => v.id === route.view) ?? VIEWS[0],
  );
</script>

<main>
  <header class="masthead">
    <h1 class="wordmark">hyndsyght</h1>
    {#if status.data}
      <a class="lamp" class:off={!status.data.daemon_running} href={buildHash("status")}>
        {status.data.daemon_running
          ? "Recording"
          : "Not recording. Start it with: hyndsyght daemon"}
      </a>
    {/if}
  </header>
  <nav>
    {#each VIEWS as view (view.id)}
      <a href={buildHash(view.id)} class:active={route.view === view.id}>{view.label}</a>
    {/each}
  </nav>
  <active.component params={route.params} />
</main>
