<script lang="ts">
  import Terminal from '$lib/components/Terminal.svelte'

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
      title: 'A dashboard with eight screens',
      body: 'Today, Stats, Timeline, Categories, Claude sessions, Focus, Human vs agent and Status. Step through days, open any 5-minute block to see its events, assign a title to a category from the timeline, and follow an agent session turn by turn. It only answers on this computer and updates itself every 15 seconds.',
      command: 'hyndsyght serve',
      output: ['Uvicorn running on http://127.0.0.1:8420', '', 'Today   Stats   Timeline   Categories', 'Claude sessions   Focus   Human vs agent   Status'],
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
        </div>
        <Terminal title="~/hyndsyght">
          <div><span class="t-prompt"></span>{feature.command}</div>
          {#each feature.output as line}
            <div>{line || ' '}</div>
          {/each}
        </Terminal>
      </div>
    </section>
  {/each}

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

  .compare { padding-top: 0; }
  .compare h2 { border-top: 2px solid var(--ink); padding-top: clamp(32px, 5vw, 56px); margin-bottom: 28px; }

  .table-scroll { overflow-x: auto; }
  .table-scroll .compare-table { min-width: 520px; }

  @media (max-width: 860px) {
    .feature-grid, .head-grid { grid-template-columns: minmax(0, 1fr); }
  }
</style>
