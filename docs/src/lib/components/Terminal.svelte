<script lang="ts">
  import type { Snippet } from 'svelte'

  // Lines print one after another when the terminal mounts. Wrap it in
  // {#key …} to replay the printout when its content changes.
  let {
    title = 'zsh',
    maxWidth = '100%',
    children,
  }: {
    title?: string
    maxWidth?: string
    children: Snippet
  } = $props()
</script>

<figure class="terminal" style:max-width={maxWidth}>
  <figcaption class="terminal-bar">{title}</figcaption>
  <div class="terminal-body">
    {@render children()}
  </div>
</figure>

<style>
  .terminal {
    background: var(--term-bg);
    color: var(--term-text);
    border-radius: 6px;
    overflow: hidden;
    width: 100%;
    box-shadow:
      0 1px 0 color-mix(in oklch, var(--ink) 30%, transparent),
      0 24px 48px -24px color-mix(in oklch, var(--ink) 55%, transparent);
  }

  .terminal-bar {
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

  .terminal-bar::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--plate);
  }

  .terminal-body {
    padding: 20px 22px 24px;
    font-family: var(--font-mono);
    font-stretch: 87.5%;
    font-size: 0.8125rem;
    line-height: 1.75;
    overflow-x: auto;
  }

  .terminal-body > :global(*) {
    white-space: pre;
    animation: print-line 0.01s both;
  }

  .terminal-body > :global(:nth-child(2)) { animation-delay: 0.35s; }
  .terminal-body > :global(:nth-child(3)) { animation-delay: 0.45s; }
  .terminal-body > :global(:nth-child(4)) { animation-delay: 0.55s; }
  .terminal-body > :global(:nth-child(5)) { animation-delay: 0.65s; }
  .terminal-body > :global(:nth-child(6)) { animation-delay: 0.75s; }
  .terminal-body > :global(:nth-child(7)) { animation-delay: 0.85s; }
  .terminal-body > :global(:nth-child(n + 8)) { animation-delay: 0.95s; }

  .terminal-body::after {
    content: '';
    display: inline-block;
    width: 0.6em;
    height: 1.15em;
    vertical-align: -0.2em;
    background: var(--plate);
    animation: blink 1.1s steps(1) infinite;
  }

  @media (max-width: 560px) {
    .terminal-body { padding: 16px; font-size: 0.75rem; }
  }

  @keyframes print-line {
    from { visibility: hidden; }
    to { visibility: visible; }
  }

  @keyframes blink {
    50% { opacity: 0; }
  }
</style>
