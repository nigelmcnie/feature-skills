---
name: feature-choice
description: "Help decide which feature to work on next when the user asks for a recommendation. Reads the project's features tracker (canonical HTML in the dev-store, repo features.md as fallback), summarises top Available candidates from their context docs, and recommends one with reasoning. Common trigger phrases: \"what should I work on next\", \"what feature should we tackle\", \"pick a feature\", \"what's next on the list\", \"I have time, what's a good thing to start\", \"decide what to work on\", \"suggest a feature\", \"any ideas for what to do next\"."
allowed-tools: Read, Grep, Glob, Bash
argument-hint: "[feature-name]"
---

# Feature Choice Workflow

You help the user decide what feature to work on next. The shape of
the question is usually "I have time, what's a good thing to start?"
— you read the tracker, skim candidate contexts, and recommend one
with a real reason.

This is a read-only advisory skill. Don't write anything; don't
auto-invoke any other skill. End by handing the user the option to
proceed.

## Step 1: Resolve project and find the tracker

```bash
PROJECT=$(basename $(git rev-parse --show-toplevel))
```

Find the features tracker, in this order:

1. `~/.claude/feature-docs/<PROJECT>/features.html` — canonical
   (dev-store).
2. `features.md` at the repo root — legacy / exported snapshot.

Call the chosen path `TRACKER`. If neither exists, the project
doesn't have a tracker. Tell the user:

> No features tracker found for **<PROJECT>**. Either:
>
> - Run `/feature` to scaffold one (offers the full workflow setup).
> - Or tell me what's been on your mind and I'll help shape it into
>   a feature.

Then stop.

## Step 2: If `$ARGUMENTS` is provided, deep-dive that one

If the user supplied a feature name (e.g. `/feature-choice rule-ir`),
they want detail on that specific feature, not a triage. Read its
context doc — prefer
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/context.html`, fall back
to `docs/features/<FEATURE>/context.md`.

Summarise:

- What it is (one sentence).
- The motivation (why it's worth doing).
- Scope hints (small / medium / large).
- Open questions or known blockers.
- Whether it's claimed (`In Progress`) or queued (`Available`).

Then ask whether they want to start it now (offer `/feature <name>`
to route to the right next stage) or hear about alternatives. Stop.

## Step 3: Parse the tracker

Read `TRACKER` and extract:

- **In Progress** rows — already claimed work (feature, owner,
  notes).
- **Available** rows — queued candidates (feature, notes).
- **Suggested order** section if present — narrative ordering
  guidance the project owner has captured. This is a strong signal
  in projects that maintain one (e.g. kea).
- **Done** rows — skip; already shipped.

For HTML trackers: parse `<section id="in-progress">`,
`<section id="available">`, `<section id="suggested-order">`. For
markdown: parse the `## In Progress` / `## Available` tables and the
`## Suggested order` prose section.

## Step 4: Skim context for top candidates

Pick up to **5 candidates** to read in detail:

- All `In Progress` items (they're claimed; the user may want to
  continue them).
- Top of `Available`, ordered by:
  1. Position in `Suggested order` if that section exists.
  2. Notes-column priority hints ("ship next", "P1", "blocked on X",
     "foundation for Y").
  3. Otherwise, tracker order.

For each candidate, locate its context doc — prefer
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/context.html`, fall back
to `docs/features/<FEATURE>/context.md`. Read enough to grasp:

- One-line summary of what it is.
- Scope / size hint.
- Dependencies on other features.
- Anything that flags it as a current priority or a deferred concern.

Skim, don't transcribe. The context doc may be 100+ lines; you need
two sentences per candidate.

## Step 5: Present and recommend

Present a structured triage in chat. Format:

> **In progress** (continue these first if any are stuck or
> half-done):
>
> 1. `<feature>` — owner: <name>. <one-line summary>.
>    <one-line status note from context if useful>.
>
> **Available** (top candidates):
>
> 1. `<feature>` — <one-line summary>. <why-this-now hint:
>    foundation work / unblocks Y / small win / etc.>
> 2. `<feature>` — …
> 3. …
>
> **My take**: I'd pick **`<feature>`** because <one paragraph of
> reasoning grounded in what the context actually says — fit with
> recent work, dependency status, scope vs likely time budget,
> whether it unblocks downstream features>.
>
> Reply with a name to dig in, "tell me more about X" for full
> context, or "actually [something else]" if none of these are
> right.

Be specific in the reasoning. Reference what's actually in the
context docs and tracker notes; don't fall back to generic
recommendations. If `Suggested order` exists, your recommendation
should usually align with it — call out explicitly if you think the
user should override.

## Step 6: Hand off

Wait for the user's response. When they pick:

- **They named a feature**: route them.
  - If it's already In Progress and has docs → suggest
    `/feature <name>` to route to the right next stage.
  - If it's Available with only a context doc → suggest
    `/feature-requirements <name>` (or `/feature <name>` if they want
    the router to decide).
  - If they want full context first → read the context doc end to
    end and summarise.
- **They want alternatives**: pick the next-most-promising candidate
  not already shown, and surface it with similar reasoning.

**Do not auto-invoke any sub-skill.** This skill ends with the user
informed; they pick the moment to start.
