<script lang="ts">
  import { base } from '$app/paths'
  import { obliterate } from 'orphan-obliterator'
  import { onMount } from 'svelte'
  import Terminal from '$lib/components/Terminal.svelte'

  type Mode = 'install' | 'run' | 'agent'
  type Tone = 'hi' | 'dim' | 'ok' | 'err'
  type Line = string | { text: string; tone: Tone }

  const wordmark = 'hyndsyght'
  let mode = $state<Mode>('install')
  let copied = $state<string | null>(null)
  let step = $state(0)

  const steps: { title: string; description: string; command: string; output: Line[] }[] = [
    {
      title: 'Set up once',
      description: 'The guided setup connects Claude Code, checks the Screen Recording permission and starts recording at login. Run it again any time; it only adds what is missing.',
      command: 'hyndsyght setup',
      output: [
        'Database + rules ready.',
        'Install Claude Code hooks for agent-activity tracking? [Y/n]',
        { text: 'Hooks: 6 added, 0 already present.', tone: 'ok' },
        { text: 'Screen Recording permission looks OK.', tone: 'ok' },
        'Start the menu-bar app at login? [Y/n]',
        { text: 'Menu-bar app installed and started.', tone: 'ok' },
      ],
    },
    {
      title: 'Check it runs',
      description: 'A health report: is the recorder running, is Claude Code connected, can it read window titles, and when did each source last report.',
      command: 'hyndsyght status',
      output: [
        { text: '✓ Daemon running', tone: 'ok' },
        { text: '✓ Claude Code hooks installed (6/6 events)', tone: 'ok' },
        { text: '✓ Screen Recording permission looks OK', tone: 'ok' },
        '✓ Database: 4.2 MB',
        { text: '    last event — afk: 2m ago · agent: 40s ago · media: 1m ago · window: 3s ago', tone: 'dim' },
      ],
    },
    {
      title: 'Tune the rules',
      description: 'Test your category and client rules against the last week of real history, with the titles that earned each hour.',
      command: 'hyndsyght categorize test --days 7',
      output: [
        { text: 'Categories', tone: 'hi' },
        '  dev       21.5h',
        { text: '            6.0h  Globex board', tone: 'dim' },
        '  meetings   4.0h',
        { text: 'Clients', tone: 'hi' },
        '  acme.globex  12.5h',
        '  initech       6.0h',
      ],
    },
    {
      title: 'Export hours',
      description: 'Hours per day and client, rounded to the quarter, ready to paste into a timesheet.',
      command: 'hyndsyght export --since 2026-09-21 --csv',
      output: [
        { text: 'date,client,hours', tone: 'dim' },
        '2026-09-21,acme.globex,5.25',
        '2026-09-21,initech,1.5',
        '2026-09-22,acme.globex,6.75',
      ],
    },
    {
      title: 'Ask your assistant',
      description: 'Connect any MCP-capable assistant and it can read summaries of your day. It cannot change anything.',
      command: 'claude "how much of today did my agent do?"',
      output: [
        { text: '⏺ hyndsyght · get_ledger_summary(day: "2026-09-25")', tone: 'dim' },
        'You spent 5h 10m at the computer. Your agent ran for 3h 40m,',
        '2h 55m of that alongside you: about 0.7 agent minutes per minute of yours.',
      ],
    },
  ]

  const commands: Record<Mode, string> = {
    install: 'git clone https://github.com/doublej/hyndsyght && cd hyndsyght && just setup',
    run: 'hyndsyght tray',
    agent: 'uv run --extra mcp hyndsyght mcp serve',
  }
  const modes = Object.keys(commands) as Mode[]

  const features = [
    { title: 'No timers to start', description: 'It records the front app and window from login onwards, and recovers from sleep and crashes on its own.' },
    { title: 'Away time, removed honestly', description: 'After five minutes without input you count as away, dated back to your last keystroke. Empty days show as missing data, not days off.' },
    { title: "Your agent's work next to yours", description: 'Every Claude Code turn is recorded with its project and intent, so you see human time, agent time and the overlap.' },
    { title: 'Private by default', description: 'Titles from password managers are never stored. Everything stays on your Mac: no account, no cloud, no telemetry.' },
    { title: 'Rules that re-label the past', description: 'Categories and clients live in one plain-text rules file. Edit a rule and all past activity follows at once.' },
    { title: 'Hours per client', description: 'Export a detailed report or a quarter-hour spreadsheet per day and client, with the evidence behind every row.' },
  ]

  onMount(() => {
    const instance = obliterate({
      selectors: ['p', '.tagline', '.description', '.feature-list dd'],
      rules: { minLastLineWords: 3, maxProtectedChars: 40 },
    })
    return () => instance.destroy()
  })

  function copyCommand(key: string, text: string) {
    navigator.clipboard.writeText(text)
    copied = key
    setTimeout(() => (copied = null), 2000)
  }
</script>

<main>
  <section class="hero plate" aria-labelledby="hero-title">
    <div class="container">
      <h1 id="hero-title" class="hero-wordmark" style:--chars={wordmark.length}>{wordmark}</h1>
      <div class="hero-grid">
        <p class="tagline">Private, automatic time tracking for your Mac, with your AI coding agent's work next to your own.</p>
        <div class="hero-install">
          <div class="mode-toggle" role="group" aria-label="Command to show">
            {#each modes as m}
              <button aria-pressed={mode === m} onclick={() => (mode = m)}>{m[0].toUpperCase() + m.slice(1)}</button>
            {/each}
          </div>
          <div class="command-box">
            <code><span class="t-prompt"></span>{commands[mode]}</code>
            <button class="copy-btn" onclick={() => copyCommand('hero', commands[mode])}>
              {copied === 'hero' ? 'Copied' : 'Copy'}
            </button>
          </div>
          <a href="https://github.com/doublej/hyndsyght" target="_blank" rel="noopener noreferrer" class="source-link">Read the source on GitHub</a>
        </div>
      </div>
    </div>
  </section>

  <section class="demo" aria-labelledby="demo-title">
    <div class="container demo-grid">
      <div class="demo-steps">
        <h2 id="demo-title">A first session</h2>
        <ol class="step-list">
          {#each steps as s, i}
            <li>
              <button aria-pressed={step === i} onclick={() => (step = i)}>
                <span class="step-num">{i + 1}</span>{s.title}
              </button>
            </li>
          {/each}
        </ol>
        <p class="description" aria-live="polite">{steps[step].description}</p>
      </div>
      {#key step}
        <Terminal title="~/hyndsyght">
          <div><span class="t-prompt"></span>{steps[step].command}</div>
          {#each steps[step].output as line}
            {#if typeof line === 'string'}
              <div>{line || ' '}</div>
            {:else}
              <div class="t-{line.tone}">{line.text}</div>
            {/if}
          {/each}
        </Terminal>
      {/key}
    </div>
  </section>

  <section class="features" aria-labelledby="features-title">
    <div class="container">
      <div class="features-grid">
        <div class="features-head">
          <h2 id="features-title">What it does</h2>
          <a href="{base}/features">All features</a>
        </div>
        <dl class="feature-list">
          {#each features as feature}
            <div>
              <dt>{feature.title}</dt>
              <dd>{feature.description}</dd>
            </div>
          {/each}
        </dl>
      </div>
    </div>
  </section>

  <section class="cta plate" aria-labelledby="cta-title">
    <div class="container cta-inner">
      <h2 id="cta-title">Install {wordmark}</h2>
      <div class="cta-action">
        <div class="command-box">
          <code><span class="t-prompt"></span>{commands.install}</code>
          <button class="copy-btn" onclick={() => copyCommand('cta', commands.install)}>
            {copied === 'cta' ? 'Copied' : 'Copy'}
          </button>
        </div>
        <p>Source, issues and releases on <a href="https://github.com/doublej/hyndsyght" target="_blank" rel="noopener noreferrer">GitHub</a>.</p>
      </div>
    </div>
  </section>
</main>

<style>
  section { padding: var(--section-padding) 0; }

  /* Hero: the plate, with the wordmark sized to fill the container width */
  .hero { padding: clamp(40px, 7vw, 88px) 0 clamp(48px, 8vw, 104px); }
  .hero .container { container-type: inline-size; }

  .hero-wordmark {
    font-family: var(--font-mono);
    font-stretch: 112.5%;
    font-weight: 800;
    /* Martian Mono at this width and tracking advances ~0.70em per glyph; 0.74 leaves slack so the name stays on one line */
    font-size: clamp(2.25rem, calc(100cqi / (var(--chars) * 0.74)), 12rem);
    line-height: 0.95;
    letter-spacing: -0.045em;
    margin: 0 0 clamp(28px, 5vw, 56px) -0.04em;
    overflow-wrap: anywhere;
  }

  .hero-grid {
    display: grid;
    grid-template-columns: minmax(0, 4fr) minmax(0, 7fr);
    gap: var(--grid-gap);
    align-items: end;
  }

  .tagline {
    font-size: clamp(1.3rem, 2.4vw, 1.75rem);
    font-weight: 500;
    line-height: 1.25;
    letter-spacing: -0.01em;
    max-width: 26ch;
  }

  .hero-install { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; }
  .hero-install > :not(.command-box) { justify-self: start; }

  .mode-toggle {
    display: inline-flex;
    border: 1.5px solid var(--ink);
    border-radius: 4px;
    overflow: hidden;
  }

  .mode-toggle button {
    border: none;
    background: transparent;
    color: var(--ink);
    font: inherit;
    font-size: 0.9rem;
    font-weight: 500;
    padding: 6px 16px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
  }

  .mode-toggle button + button { border-left: 1.5px solid var(--ink); }
  .mode-toggle button[aria-pressed='true'] { background: var(--ink); color: var(--paper); }

  .command-box {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    width: 100%;
    background: var(--term-bg);
    color: var(--term-text);
    border-radius: 4px;
    padding: 10px 10px 10px 18px;
  }

  .command-box code {
    min-width: 0;
    font-size: 0.875rem;
    overflow-x: auto;
    white-space: nowrap;
    padding: 4px 0;
  }

  .copy-btn {
    flex-shrink: 0;
    border: 1px solid color-mix(in oklch, var(--term-text) 30%, transparent);
    background: transparent;
    color: var(--term-text);
    font: inherit;
    font-size: 0.85rem;
    font-weight: 500;
    min-width: 5.5em;
    padding: 6px 12px;
    border-radius: 3px;
    cursor: pointer;
    transition: background 0.15s;
  }

  .copy-btn:hover { background: color-mix(in oklch, var(--term-text) 12%, transparent); }
  .copy-btn:focus-visible { outline-color: var(--plate); }

  .source-link { font-weight: 500; margin-top: 4px; }

  /* Demo: the step list is a real sequence, so it is numbered */
  .demo-grid {
    display: grid;
    grid-template-columns: minmax(0, 4fr) minmax(0, 7fr);
    gap: var(--grid-gap);
    align-items: start;
  }

  .demo h2, .features h2 {
    font-size: clamp(1.75rem, 3.4vw, 2.5rem);
    font-weight: 600;
    letter-spacing: -0.02em;
    margin-bottom: 24px;
  }

  .step-list { list-style: none; display: grid; gap: 4px; margin-bottom: 20px; }

  .step-list button {
    display: flex;
    align-items: center;
    gap: 14px;
    width: 100%;
    border: none;
    background: none;
    color: var(--ink-faint);
    font: inherit;
    font-size: 1.125rem;
    font-weight: 500;
    text-align: left;
    padding: 8px 0;
    cursor: pointer;
    transition: color 0.15s;
  }

  .step-list button:hover, .step-list button[aria-pressed='true'] { color: var(--ink); }

  .step-num {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    flex-shrink: 0;
    border: 1.5px solid currentColor;
    border-radius: 3px;
    font-size: 0.875rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
    transition: background 0.15s;
  }

  .step-list button[aria-pressed='true'] .step-num { background: var(--plate); border-color: var(--ink); }

  .description { color: var(--ink-soft); max-width: 38ch; min-height: 3.1em; }

  /* Keep the page still while steps with different output lengths swap in */
  .demo-grid :global(.terminal-body) { min-height: 11em; }

  /* Features: a definition list, not cards */
  .features { padding-top: 0; }

  .features-grid {
    display: grid;
    grid-template-columns: minmax(0, 4fr) minmax(0, 7fr);
    gap: var(--grid-gap);
    border-top: 2px solid var(--ink);
    padding-top: clamp(32px, 5vw, 56px);
  }

  .features-head a { font-weight: 500; }

  .feature-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: clamp(28px, 4vw, 44px) var(--grid-gap);
  }

  .feature-list dt {
    display: flex;
    align-items: baseline;
    gap: 10px;
    font-size: 1.25rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    margin-bottom: 6px;
  }

  .feature-list dt::before {
    content: '';
    width: 10px;
    height: 10px;
    flex-shrink: 0;
    background: var(--plate);
    box-shadow: inset 0 0 0 1.5px var(--ink);
  }

  .feature-list dd { color: var(--ink-soft); padding-left: 20px; }

  /* CTA: the plate again, closing the page */
  .cta-inner {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 20px var(--grid-gap);
    align-items: end;
  }

  .cta-action { display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px; }

  .cta h2 {
    font-size: clamp(2rem, 5vw, 3.5rem);
    font-weight: 700;
    letter-spacing: -0.03em;
  }


  @media (max-width: 860px) {
    .hero-grid, .demo-grid, .features-grid, .cta-inner { grid-template-columns: minmax(0, 1fr); }
    .hero-grid { gap: 28px; }
    .description { min-height: 0; }
  }

  @media (max-width: 560px) {
    .feature-list { grid-template-columns: minmax(0, 1fr); }
    .command-box { padding-left: 14px; }
    .command-box code { font-size: 0.8rem; }
  }
</style>
