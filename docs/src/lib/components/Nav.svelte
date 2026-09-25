<script lang="ts">
  import { base } from '$app/paths'
  import { page } from '$app/state'

  // Edit this list to match the pages you create. Keep GitHub last.
  const links = [
    { href: `${base}/`, label: 'Home' },
    { href: `${base}/features`, label: 'Features' },
    { href: 'https://github.com/doublej/hyndsyght', label: 'GitHub', external: true },
  ]

  function isActive(href: string): boolean {
    if (href.startsWith('http')) return false
    const path = page.url?.pathname ?? ''
    if (href === `${base}/`) return path === `${base}/` || path === base
    return path.startsWith(href)
  }
</script>

<nav aria-label="Main">
  <div class="nav-inner">
    <a href="{base}/" class="wordmark"><span class="mark" aria-hidden="true"></span>hyndsyght</a>
    <div class="nav-links">
      {#each links as link}
        <a
          href={link.href}
          class:active={isActive(link.href)}
          aria-current={isActive(link.href) ? 'page' : undefined}
          target={link.external ? '_blank' : undefined}
          rel={link.external ? 'noopener noreferrer' : undefined}
        >
          {link.label}
        </a>
      {/each}
    </div>
  </div>
</nav>

<style>
  nav {
    position: sticky;
    top: 0;
    z-index: 100;
    background: color-mix(in oklch, var(--paper) 84%, transparent);
    backdrop-filter: blur(14px) saturate(1.4);
    -webkit-backdrop-filter: blur(14px) saturate(1.4);
    border-bottom: 1px solid color-mix(in oklch, var(--ink) 10%, transparent);
  }

  .nav-inner {
    max-width: var(--container-max-width);
    margin: 0 auto;
    padding: 0 var(--container-padding);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    height: 56px;
  }

  .wordmark {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    font-family: var(--font-mono);
    font-stretch: 112.5%;
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--ink);
    text-decoration: none;
    white-space: nowrap;
  }

  .mark {
    width: 14px;
    height: 14px;
    background: var(--plate);
    box-shadow: inset 0 0 0 1.5px var(--ink);
  }

  .nav-links {
    display: flex;
    align-items: center;
    gap: clamp(12px, 3vw, 28px);
  }

  .nav-links a {
    font-size: 0.95rem;
    font-weight: 500;
    color: var(--ink-soft);
    text-decoration: none;
    padding: 6px 0;
    border-bottom: 2px solid transparent;
    transition: color 0.15s, border-color 0.15s;
  }

  .nav-links a:hover {
    color: var(--ink);
  }

  .nav-links a.active {
    color: var(--ink);
    border-bottom-color: var(--plate);
  }

  @media (max-width: 480px) {
    .wordmark { font-stretch: 100%; font-size: 0.85rem; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
    .nav-links { flex-shrink: 0; }
  }
</style>
