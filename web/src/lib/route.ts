// Hash-based routing: `#/events?source=agent&since=…`. The hash never
// reaches the server, so filter state is deep-linkable with no backend
// SPA-fallback route needed.

export interface Route {
  view: string;
  params: URLSearchParams;
}

const DEFAULT_VIEW = "overview";

export function parseHash(hash: string): Route {
  const raw = hash.replace(/^#\/?/, "");
  const [view, query] = raw.split("?");
  return { view: view || DEFAULT_VIEW, params: new URLSearchParams(query ?? "") };
}

export function buildHash(
  view: string,
  params: Record<string, string | undefined> = {},
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value);
  }
  const query = search.toString();
  return `#/${view}${query ? `?${query}` : ""}`;
}
