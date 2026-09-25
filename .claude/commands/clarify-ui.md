Make hyndsyght read and behave like a tool a person built for themselves, not like generated software.

Target: $ARGUMENTS — if empty, every view in `web/src/views/` plus `src/hyndsyght/cli.py` output.
Rules to apply: `.claude/rules/ui-copy.md`. Read it first; it is the standard, this prompt is the procedure.

## Do this per view, one view at a time

1. **Read the view and its data.** Open the `.svelte` file and the `lib/api.ts` calls it makes.
   Write down, in one sentence, the single question this view answers for the user
   ("where did today go?", "what is the daemon doing right now?"). If you cannot state it in
   one sentence, the view has two jobs — say so and propose the split before editing.

2. **Judge it against three questions:**
   - *Copy:* would I say this sentence out loud to someone sitting next to me? Every label,
     button, heading, empty state, error, tooltip.
   - *Hierarchy:* is the answer to the view's one question the largest, first thing on screen?
     Everything that is not that answer is secondary, smaller, or gone.
   - *Flow:* how many clicks from opening the view to the answer? Every click that is not the
     user changing their mind is a defect. Remove it — better default, inline edit, direct link.

3. **Report before you edit.** A short table: element, what is wrong, what it becomes.
   Group as `copy` / `layout` / `flow`. No prose around it.

4. **Apply it.** Rewrite the strings, restructure the markup, delete what earns nothing.

## Boundaries

- Copy, layout, and interaction only. Do not change API shapes, store schemas, or daemon logic.
  If a copy fix needs a new field, note it and move on — do not build it.
- No new dependencies, no component library, no design-system refactor. Plain Svelte, the
  existing `StatCard` / `BarList` / `DateRange` components, existing CSS in `app.css`.
- Do not add views, modals, tabs, wizards, or onboarding. Deleting one of those is welcome.
- Do not touch generated files, `dist/`, or `node_modules/`.

## What "better" looks like here

hyndsyght shows a person where their time went. That means: real numbers, dense but calm,
sorted by size, no decoration that does not encode data. The user opens it, reads one number,
and closes it. Optimise for that trip, not for time spent in the app.

Concretely, prefer:
- A number and its unit over a sentence containing a number.
- A sorted list over a chart, unless the shape over time is the point.
- Relative time the user thinks in (`today`, `this week`, `since 09:00`) over ISO strings.
- Empty state that names the one action that fills it.
- Errors that name the command or setting that fixes them.

## Finish

- Run `cd web && bun run build` and `just check`. Fix what breaks.
- Commit per view: `ui: clarify <ViewName>`.
- End with the list of things you found but deliberately did not change, one line each.
