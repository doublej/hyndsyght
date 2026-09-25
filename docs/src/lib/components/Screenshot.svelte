<script lang="ts">
  import { base } from '$app/paths'

  // A dashboard screen in the same window chrome as Terminal. `screen` is the
  // file name under static/screens/ and the dashboard's own #hash route.
  let { screen, alt, height = 1000 }: { screen: string; alt: string; height?: number } = $props()
</script>

<figure class="screenshot">
  <figcaption class="screenshot-bar">127.0.0.1:8420/#{screen}</figcaption>
  <img
    src="{base}/screens/{screen}.webp"
    {alt}
    width="1136"
    {height}
    loading="lazy"
    decoding="async"
  />
</figure>

<style>
  .screenshot {
    border-radius: 6px;
    overflow: hidden;
    background: var(--paper);
    box-shadow:
      0 0 0 1px color-mix(in oklch, var(--ink) 18%, transparent),
      0 24px 48px -24px color-mix(in oklch, var(--ink) 55%, transparent);
  }

  .screenshot-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    background: var(--term-bar);
    color: var(--term-dim);
    font-family: var(--font-mono);
    font-stretch: 87.5%;
    font-size: 0.75rem;
  }

  .screenshot-bar::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--plate);
  }

  img { display: block; width: 100%; height: auto; }
</style>
