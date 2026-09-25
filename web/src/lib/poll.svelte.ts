import { apiGet } from "./api";

// Shared polling pattern (document.hidden gate, setInterval, visibilitychange
// cleanup) previously copy-pasted across every tab component. `url` is a
// getter, not a static string, so a reactive filter change re-triggers the
// effect and refetches.
export function poll<T>(url: () => string, intervalMs = 15_000) {
  let data = $state<T | null>(null);
  let error = $state<string | null>(null);

  async function refresh(path: string) {
    if (document.hidden) return;
    try {
      data = await apiGet<T>(path);
      error = null;
    } catch (e) {
      error = (e as Error).message;
    }
  }

  $effect(() => {
    const path = url();
    refresh(path);
    const interval = setInterval(() => refresh(path), intervalMs);
    const onVisible = () => refresh(path);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisible);
    };
  });

  return {
    get data() {
      return data;
    },
    get error() {
      return error;
    },
    refresh: () => refresh(url()),
  };
}
