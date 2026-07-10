---
name: feature-choice
description: "Help decide which feature to work on next when the user asks for a recommendation. Reads the project's feature tracker and candidate context docs from the webapp DB (the source of truth) via its local API, summarises top Available candidates, and recommends one with reasoning. Common trigger phrases: \"what should I work on next\", \"what feature should we tackle\", \"pick a feature\", \"what's next on the list\", \"I have time, what's a good thing to start\", \"decide what to work on\", \"suggest a feature\", \"any ideas for what to do next\"."
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

The tracker and every context doc live in the **webapp DB** — that is
the source of truth. Read them through the local API at
`http://127.0.0.1:8800`. Exported files (`features.html`, `features.md`,
`context.html`, `context.md`) are snapshots, not the truth; only read
them as a fallback when the webapp is unreachable.

## Step 1: Resolve project and load the tracker

```bash
PROJECT=$(basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")")
# Resolve the bundled webapp helper (see docs/webapp-helper.md); BASE is this
# skill's base directory, shown at the top of the invocation.
WEBAPP="$(dirname "$(readlink -f "BASE")")/bin/webapp"
```

Load the tracker from the DB:

```bash
"$WEBAPP" get /api/projects/$PROJECT/features
```

A `200` returns `{"project": "...", "features": [{"slug", "status",
"owner", "notes"}, ...]}`. This is the canonical tracker — use it.

**If the webapp is unreachable** (the helper exits non-zero / connection
refused), fall back to an exported snapshot, in this order, and note to the
user that you're reading a possibly-stale export:

1. `~/.claude/feature-docs/<PROJECT>/features.html` — dev-store export.
2. `features.md` at the repo root — older export.

**If neither the API nor a fallback yields any features** — the API
errors and no export exists, or the project is unknown to the webapp
(`"$WEBAPP" get /api/projects` doesn't list it) and
has no export — the project doesn't have a tracker. Tell the user:

> No features tracker found for **<PROJECT>**. Either:
>
> - Run `/feature` to scaffold one (offers the full workflow setup).
> - Or tell me what's been on your mind and I'll help shape it into
>   a feature.

Then stop.

## Step 2: If `$ARGUMENTS` is provided, deep-dive that one

If the user supplied a feature name (e.g. `/feature-choice rule-ir`),
they want detail on that specific feature, not a triage. Read its
context doc from the DB:

```bash
"$WEBAPP" get /api/documents/$PROJECT/$FEATURE/context/1
```

A `200` gives a JSON object with a `sections` array of
`{"key": "...", "body": "..."}` objects (keys: `problem-space`,
`related-work`, `constraints`, `links`, `open-questions`). A `404`
means no context doc was authored — fall back to
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/context.html`, then
`docs/features/<FEATURE>/context.md`, if either exists.

Summarise:

- What it is (one sentence).
- The motivation (why it's worth doing).
- Scope hints (small / medium / large).
- Open questions or known blockers.
- Its status from the tracker row: `in_progress` (claimed),
  `available` (queued), or `parked` (deferred).

Then ask whether they want to start it now (offer `/feature <name>`
to route to the right next stage) or hear about alternatives. Stop.

## Step 3: Bucket the tracker by status

From the `features` array, group rows by `status`:

- **`in_progress`** — already claimed work (slug, owner, notes).
- **`available`** — queued candidates (slug, notes).
- **`parked`** — deferred; mention only if nothing else is queued or
  the user asks.
- **`done`** / **`archived`** — skip; already shipped or dropped.

The tracker may also carry a **suggested order** — a curated ranking
the project owner maintains, rendered as its own section. This is a
strong signal in projects that keep one (e.g. kea); when present, it's
your primary ordering signal. Look for it in the tracker response from
the API; if you fell back to a file tracker, parse its
`<section id="suggested-order">` / `## Suggested order` section.

Do **not** infer priority from the order rows appear in the API
`features` array — that order is not meaningful (e.g. alphabetical).
Where there's no suggested order, fall back to the priority hints in
each row's `notes` ("ship next", "P1", "foundation for Y", "blocked
on X").

## Step 4: Skim context for top candidates

Pick up to **5 candidates** to read in detail:

- All `in_progress` items (they're claimed; the user may want to
  continue them).
- Top of `available`, ordered by:
  1. Position in the **suggested order** if the tracker has one.
  2. Notes-column priority hints ("ship next", "P1", "blocked on X",
     "foundation for Y").

For each candidate, read its context doc from the DB:

```bash
"$WEBAPP" get /api/documents/$PROJECT/$FEATURE/context/1
```

A `404` means no context doc — fall back to
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/context.html`, then
`docs/features/<FEATURE>/context.md`. If none exist, lean on the
tracker `notes` alone for that candidate.

Read enough to grasp:

- One-line summary of what it is.
- Scope / size hint.
- Dependencies on other features.
- Anything that flags it as a current priority or a deferred concern.

Skim, don't transcribe. The context doc may be long; you need two
sentences per candidate.

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
recommendations. If the tracker has a suggested order, your
recommendation should usually align with it — call out explicitly if
you think the user should override.

## Step 6: Hand off

Wait for the user's response. When they pick:

- **They named a feature**: route them.
  - If it's already `in_progress` and has docs → suggest
    `/feature <name>` to route to the right next stage.
  - If it's `available` with only a context doc → suggest
    `/feature-requirements <name>` (or `/feature <name>` if they want
    the router to decide).
  - If they want full context first → read the context doc end to
    end and summarise.
- **They want alternatives**: pick the next-most-promising candidate
  not already shown, and surface it with similar reasoning.

**Do not auto-invoke any sub-skill.** This skill ends with the user
informed; they pick the moment to start.
