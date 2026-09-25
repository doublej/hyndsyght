<script lang="ts">
  let { since = $bindable(), until = $bindable() }: { since?: number; until?: number } =
    $props();

  function toDateInput(ts?: number): string {
    return ts ? new Date(ts * 1000).toISOString().slice(0, 10) : "";
  }

  function onSinceInput(e: Event) {
    const value = (e.target as HTMLInputElement).value;
    since = value ? new Date(value).getTime() / 1000 : undefined;
  }

  function onUntilInput(e: Event) {
    const value = (e.target as HTMLInputElement).value;
    until = value ? new Date(value).getTime() / 1000 + 86400 - 1 : undefined;
  }

  function setToday() {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    since = start.getTime() / 1000;
    until = Date.now() / 1000;
  }

  function setRange(days: number) {
    until = Date.now() / 1000;
    since = until - days * 86400;
  }
</script>

<div class="toolbar">
  <input type="date" value={toDateInput(since)} oninput={onSinceInput} />
  <span class="muted">to</span>
  <input type="date" value={toDateInput(until)} oninput={onUntilInput} />
  <button class="btn" onclick={setToday}>Today</button>
  <button class="btn" onclick={() => setRange(7)}>7d</button>
  <button class="btn" onclick={() => setRange(30)}>30d</button>
</div>
