---
name: feature-implement
description: Implement one phase of a planned feature. Use after the plan is approved, when the user says it's time to implement or start building, or when there is a plan with unchecked phases. Re-invoke for each subsequent phase.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
argument-hint: "[feature-name]"
---

# Implementation Workflow

You are implementing one phase of a feature according to its approved plan.
Each invocation of this skill implements one phase and creates one MR.
Re-invoke for subsequent phases.

## Model check

Check your system context for the model you are running on. If your model name does not contain "sonnet", warn the user:

> ⚠️ This skill expects Claude Sonnet. You appear to be on [model name]. Sonnet is recommended here — implementation follows a detailed plan and doesn't need Opus-level reasoning. Continue anyway?

Wait for their response. If they say no, stop here.

## Current branch
!`git branch --show-current`

## Step 0: Read the plan

Resolve `PROJECT` once: `PROJECT=$(basename $(git rev-parse --show-toplevel))`.
`$ARGUMENTS` is the feature name (FEATURE).

Locate the plan, in this order of preference:

1. `~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html` — the
   canonical HTML in the dev-store. Use this when it exists.
2. Otherwise `docs/features/<FEATURE>/plan.md` — the legacy markdown
   plan (for features planned before the HTML migration).

Call the chosen path `PLAN_PATH` and remember which format it is.

### Find the first unchecked phase

**HTML plan**: every checklist `<li>` carries
`data-checklist-item="phase-<N>-<step>"`. An item is checked when its
`<input>` element has the `checked` attribute. Walk the items in
document order and find the smallest phase number `N` that still has
at least one item without `checked`. That's the phase you're about
to implement.

A quick scan:

```bash
grep -oE 'data-checklist-item="phase-[0-9]+-[0-9]+"[^>]*><input[^>]*>' "$PLAN_PATH" \
  | grep -v ' checked'
```

The first matching line names the next phase via its
`phase-<N>-<step>` ID.

**Markdown plan**: find the first unchecked `- [ ]` item in the
checklist. The phase number is the most recent `### Phase N:` header
preceding it.

If all items are checked, tell the user the feature is fully
implemented and suggest running manual verification — and stop. Do
not proceed to the branch check.

Note the phase number (N) — this is the phase you are about to
implement.

## Step 1: Branch check

The branch for this phase must be `features/<FEATURE>-p<N>` (always include
the phase number, even for single-phase features — use `-p1`).

- If you're already on it, proceed.
- If you're on `main` or the project's default branch, create it:
  ```bash
  git checkout -b features/<FEATURE>-p<N>
  ```
- If you're on a different branch (including a `features/...` branch that
  doesn't match this pattern), stop and ask the user before switching.

Tell the user you've switched to a new branch. Never commit implementation
work directly to the default branch.

## Step 2: Implement the phase

Work through the phase's checklist items. For each item:

1. Make the change.
2. Check off the item in the plan document (see below).

Use a capable but cost-effective model — the plan is detailed enough
that you should not need to make significant design decisions.

### Checking off an item

**HTML plan** (`plan.html` in dev-store): edit `$PLAN_PATH` and add
the `checked` attribute to the `<input>` inside the matching
`<li data-checklist-item="phase-<N>-<step>">`:

```
<li data-checklist-item="phase-1-3"><input type="checkbox"><span class="label">…</span></li>
```

becomes

```
<li data-checklist-item="phase-1-3"><input type="checkbox" checked><span class="label">…</span></li>
```

Use the `data-checklist-item` ID to locate the right `<input>`. IDs
are stable across re-renders — don't pattern-match by item text. No
markdown re-export: `plan.md` (if it was exported at handoff) is a
post-approval snapshot, deliberately frozen at the start of
implementation.

**Markdown plan** (legacy): change `- [ ]` to `- [x]` for the
matching item.

## Step 2.5: Verify "Verify" items empirically

Items in the checklist that begin with "Verify" — or that appear under
"Done when:" — typically specify a shell command (`uv build`, `unzip -l`,
`claude --print`, an end-to-end CLI invocation, etc.). Before checking
these off, **run the command and confirm the output**. Don't tick
based on having written code that *should* satisfy the criterion.

This is where the trust-the-checklist failure mode lives: an agent
writes the implementation, infers from the code that the verification
should pass, and ticks the box without confirming. The reviewer (or
the next session) then trusts the box and ships a broken state.

## Step 3: Handle deviations

If implementation reveals the plan needs to change:

- For minor deviations (same approach, different details): update
  `$PLAN_PATH` inline, note what changed and why, continue. For the
  HTML plan, edit the relevant `<section>` body directly. No
  re-export.
- For significant deviations (different approach or scope): stop,
  explain the situation to the user, and get approval on the revised
  plan before continuing. Do not silently diverge from the approved
  plan.

## Step 4: Quality control

Before committing, invoke `/feature-qa` and work through all checks it
defines. Do not rely on having run QC incrementally — do a full pass now.

## Step 5: Commit and create MR

Commit with a clear message referencing the feature and phase. Push the
branch. Create an MR for this phase.

## Step 6: Verification guidance

Tell the user what to manually verify to confirm this phase is working.
Even if automated tests pass, give the human concrete steps:
- What to run or observe
- What the expected outcome looks like
- Any specific channels, dashboards, or CLI commands to check

Keep this brief and actionable. The human should be able to follow these
steps immediately after the MR is merged.

If there are subsequent phases, tell the user to say something like "next
phase" or "continue" once this MR is merged — you will automatically
re-invoke `/feature-implement $ARGUMENTS` when they do. Before re-invoking,
explicitly ask: "Has the MR for this phase been merged?" Do not start the
next phase until they confirm — starting phase N on an unmerged phase N-1
branch causes conflicts.

If all phases are now complete, tell the user:

> All phases implemented. When you're ready to review, switch to your Opus
> session and run `/feature-review <FEATURE>`.

Do not invoke `/feature-review` yourself.
