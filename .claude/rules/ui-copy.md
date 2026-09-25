---
paths:
  - "web/src/**"
  - "src/hyndsyght/cli.py"
  - "src/hyndsyght/insights/**"
  - "src/hyndsyght/categorize/**"
---

# Copy and UI rules

Everything a user reads or clicks in hyndsyght. Applies to Svelte views, CLI output,
error messages, empty states, and anything an LLM produces that reaches a screen.

## Voice

Write the sentence a colleague would say out loud, then delete the half that was throat-clearing.

- Sentence case for labels, buttons, headings. Not Title Case.
- Second person, present tense. "Your day starts at 09:00", not "The user's day begins".
- One idea per sentence. If it needs a semicolon or an em dash, split it.
- Numbers beat adjectives. "4h 12m on Sonic Router" — never "a productive session".
- No exclamation marks, no praise, no emoji in UI chrome.
- British/Dutch-neutral plain English; no idioms.

## Banned

These are the tell. If one appears, the copy is wrong:

`seamlessly`, `effortlessly`, `powerful`, `robust`, `leverage`, `unlock`, `dive in`,
`at a glance` (unless literally true), `insights at your fingertips`, `supercharge`,
`journey`, `elevate`, `curated`, `AI-powered`, `smart` as a feature adjective,
`Let's get started`, `Oops`, `Something went wrong`, `We're sorry`.

Also banned as a shape: the "it's not X, it's Y" construction, three-item lists used for
rhythm rather than content, and any sentence whose only job is to introduce the next one.

## Specific surfaces

| Surface | Rule |
|---|---|
| Button | Verb naming the result: `Start timer`, `Merge categories`, `Export CSV`. Never `Get started`, `Continue`, `Submit`. |
| Empty state | One line: what appears here + the single action that fills it. `No events yet. Start the daemon to begin tracking.` |
| Error | What happened, then what to do. `Daemon not running. Start it with: hyndsyght daemon start`. No apology, no blame. |
| Loading | Keep layout stable, reserve the space. Show the previous value greyed rather than a spinner where a stale number is still useful. |
| Tooltip | Only for information that does not fit; never a restatement of the label. |
| Confirmation | Only for destructive and irreversible. Everything else gets undo or nothing. |

## Flow

- One primary action per view. Everything else is secondary or hidden.
- No wizard where one form fits. No modal where inline editing fits. No new view where a row expands.
- Show the data, not a paragraph about the data. If it matters it is a number, a bar, or a sorted list.
- Defaults over settings. Add a setting only when two real users would set it differently.
- Never make the user name, categorize, or configure something the app can infer and let them correct later.

## LLM output

The LLM classifies and extracts. It does not talk to the user.

- Model output enters the UI as **data** — a category, a score, a label — rendered by the same
  deterministic components as everything else. Never render generated prose in a view.
- Every LLM decision is correctable in one click, and the correction persists as a rule that
  outranks the model next time.
- Show confidence as a state (`uncertain`, needs review), never as hedged prose.
- No chat box. The user's questions about their own time are answered by filters and ranges.
- Insight = a sentence template filled with computed numbers, or nothing. If there is no number
  worth reporting, render nothing rather than a generated observation.

## Check

Read the string aloud. If you would not say it to a person standing next to you, rewrite it.
Then cut it by a third.
