<script lang="ts">
  import Terminal from '$lib/components/Terminal.svelte'
  import Screenshot from '$lib/components/Screenshot.svelte'

  const features = [
    {
      title: 'Capture, and pause when you want',
      body: 'The recorder notes the front app and window title every few seconds, when you step away, what Spotify or Apple Music is playing, and every Claude Code turn with its project and intent. Titles from password managers are never stored. Pause for 15 minutes, an hour or until you resume from the menu bar; away detection and agent tracking keep running.',
      command: 'hyndsyght tray',
      output: ['Today: 5h 10m', 'Now: Code · days.py — hyndsyght', '', 'Open dashboard', 'Pause tracking  ›  15 minutes · 1 hour · Until I resume', 'Restart daemon', 'Quit hyndsyght'],
    },
    {
      title: 'Categories, clients and projects',
      body: 'One plain-text rules file maps titles to categories and clients. The most specific match wins, and editing a rule re-labels all past activity at once. A terminal or editor window takes the project of the agent session running next to it. Preview any title before you commit to a rule.',
      command: 'hyndsyght categorize preview "Globex board - Google Chrome"',
      output: ['dev.browser'],
    },
    {
      title: 'Export your hours',
      body: 'A detailed report per local day with human time, unclassified time and one row per project, client and category, each with the top apps and titles as evidence. Or a spreadsheet with quarter-hour lines per day and client. Row IDs stay the same across re-exports.',
      command: 'hyndsyght export --since 2026-09-21 --csv',
      output: ['date,client,hours', '2026-09-21,acme.globex,5.25', '2026-09-21,initech,1.5', '2026-09-22,acme.globex,6.75'],
    },
    {
      title: 'Read-only access for your AI assistant',
      body: 'An MCP server lets an assistant list recent events, get a day\'s focus summary and the human vs agent split. Titles are hidden unless it asks for them, and it can never change your data. The numbers match the dashboard.',
      command: 'uv run --extra mcp hyndsyght mcp serve',
      output: ['list_recent_events', 'get_attention_summary', 'get_ledger_summary'],
    },
    {
      title: 'Bring your ActivityWatch history',
      body: 'Coming from ActivityWatch? Open Status in the dashboard and pick the computers whose window and away history you want. Titles on your hidden list stay out. The import stops where hyndsyght started recording, so no minute counts twice. You can remove it again at any time.',
      command: 'hyndsyght import activitywatch --dry-run',
      output: [],
      screen: 'import',
    },
  ]

  const screens = [
    { screen: 'overview', title: 'Today', body: 'Your day in 5-minute blocks, compared with the same time of day over the week before.' },
    { screen: 'stats', title: 'Stats', body: 'Seven, 30 or 90 days: active time per day, when you tend to work, and your longest runs.' },
    { screen: 'events', title: 'Timeline', body: 'Every raw event, filterable and shareable, with one click to put a title in a category.' },
    { screen: 'categories', title: 'Categories', body: 'Time per category, a live preview for any title, and patterns you add or remove in place.' },
    { screen: 'agents', title: 'Claude sessions', body: 'Recent sessions with their turns, sub-agents, agent time and last intent, and a trail per session.' },
    { screen: 'attention', title: 'Focus', body: 'Your longest unbroken stretch, switches per hour and median session, with a 14-day trend.' },
    { screen: 'ledger', title: 'Human vs agent', body: "Your minutes, your agents' minutes and the overlap, with a 14-day trend." },
    { screen: 'status', title: 'Status', body: 'Is it recording, is Claude Code connected, can it read window titles, and when each source last reported.' },
  ]

  const alternatives = ['ActivityWatch', 'Timing', 'Toggl Track']
  const comparison = [
    { aspect: 'Automatic capture', ours: 'Yes', others: ['Yes', 'Yes', 'Timers, optional tracking'] },
    { aspect: 'Local only', ours: 'Yes', others: ['Yes', 'Optional sync', 'No, cloud'] },
    { aspect: 'AI-agent aware', ours: 'Claude Code turns and sub-agents', others: ['No', 'No', 'No'] },
    { aspect: 'Hours export per client', ours: 'Report and CSV', others: ['Raw data export', 'Yes', 'Yes'] },
  ]
</script>

<main>
  <section class="page-head plate" aria-labelledby="page-title">
    <div class="container head-grid">
      <h1 id="page-title">What <span class="name">hyndsyght</span> does</h1>
      <p class="subtitle">Private, automatic time tracking for your Mac, with your AI coding agent's work next to your own.</p>
    </div>
  </section>

  {#each features as feature, i}
    <section class="feature" aria-labelledby="feature-{i}">
      <div class="container feature-grid">
        <div>
          <h2 id="feature-{i}">{feature.title}</h2>
          <p>{feature.body}</p>
          {#if feature.screen}
            <p class="cli">From the command line: <code>{feature.command}</code></p>
          {/if}
        </div>
        {#if feature.screen}
          <Screenshot screen={feature.screen} alt="The import wizard in the hyndsyght dashboard, showing two computers found in ActivityWatch." height={540} />
        {:else}
          <Terminal title="~/hyndsyght">
            <div><span class="t-prompt"></span>{feature.command}</div>
            {#each feature.output as line}
              <div>{line || ' '}</div>
            {/each}
          </Terminal>
        {/if}
      </div>
    </section>
  {/each}

  <section class="dashboard" id="dashboard" aria-labelledby="dashboard-title">
    <div class="container">
      <div class="feature-grid">
        <h2 id="dashboard-title">A dashboard with eight screens</h2>
        <p>Open it from the menu bar, or run <code>hyndsyght serve</code>. It answers only on this computer and updates itself every 15 seconds. Every screen has its own address, so Back, Forward and bookmarks work.</p>
      </div>
      <ul class="gallery">
        {#each screens as s}
          <li>
            <Screenshot screen={s.screen} alt="The {s.title} screen of the hyndsyght dashboard, showing demo data." />
            <h3>{s.title}</h3>
            <p>{s.body}</p>
          </li>
        {/each}
      </ul>
    </div>
  </section>

  <section class="compare" aria-labelledby="compare-title">
    <div class="container">
      <h2 id="compare-title">Compared with the alternatives</h2>
      <div class="table-scroll">
        <table class="compare-table">
          <thead>
            <tr>
              <td></td>
              <th scope="col" class="ours">hyndsyght</th>
              {#each alternatives as name}<th scope="col">{name}</th>{/each}
            </tr>
          </thead>
          <tbody>
            {#each comparison as row}
              <tr>
                <th scope="row">{row.aspect}</th>
                <td class="ours">{row.ours}</td>
                {#each row.others as cell}<td>{cell}</td>{/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  </section>
</main>

<style>
  section { padding: var(--section-padding) 0; }

  .page-head { padding: clamp(48px, 8vw, 96px) 0; }

  h1 {
    font-size: clamp(2.25rem, 6vw, 4.5rem);
    font-weight: 700;
    letter-spacing: -0.035em;
    max-width: 16ch;
  }

  .name { white-space: nowrap; }

  .head-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 20px var(--grid-gap);
    align-items: end;
  }

  .subtitle { font-size: clamp(1.15rem, 2vw, 1.4rem); font-weight: 500; max-width: 36ch; line-height: 1.35; }

  .feature + .feature { padding-top: 0; }

  .feature-grid {
    display: grid;
    grid-template-columns: minmax(0, 4fr) minmax(0, 7fr);
    gap: var(--grid-gap);
    align-items: start;
  }

  h2 {
    font-size: clamp(1.5rem, 3vw, 2.25rem);
    font-weight: 600;
    letter-spacing: -0.02em;
    margin-bottom: 14px;
  }

  .feature p { color: var(--ink-soft); max-width: 40ch; }
  .feature .cli { margin-top: 14px; font-size: 0.9rem; }

  .dashboard { padding-top: 0; }
  .dashboard .feature-grid { align-items: end; margin-bottom: clamp(32px, 5vw, 56px); }
  .dashboard .feature-grid h2 { margin-bottom: 0; }
  .dashboard .feature-grid p { color: var(--ink-soft); max-width: 52ch; }

  .gallery {
    list-style: none;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: clamp(36px, 5vw, 64px) var(--grid-gap);
  }

  .gallery h3 { font-size: 1.25rem; font-weight: 600; letter-spacing: -0.01em; margin: 18px 0 4px; }
  .gallery p { color: var(--ink-soft); max-width: 44ch; }

  .compare { padding-top: 0; }
  .compare h2 { border-top: 2px solid var(--ink); padding-top: clamp(32px, 5vw, 56px); margin-bottom: 28px; }

  .table-scroll { overflow-x: auto; }
  .table-scroll .compare-table { min-width: 520px; }

  @media (max-width: 860px) {
    .feature-grid, .head-grid, .gallery { grid-template-columns: minmax(0, 1fr); }
  }
</style>
