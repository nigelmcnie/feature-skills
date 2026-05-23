---
name: feature
description: Start or continue work on a feature. Checks current state and routes to the right stage of the feature workflow (requirements → plan → implement → review).
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
argument-hint: "[feature-name]"
---

# Feature Workflow Router

Route to the right stage of the feature workflow based on current state.

## Step 1: Establish the feature name

If `$ARGUMENTS` is provided, use it as the feature name (FEATURE).

If not, check for `features.md` at the repo root:
- If present, show its In Progress and Available sections and ask which feature the user wants to work on.
- If absent, ask the user what the feature is. Pick a short kebab-case name with them and confirm it. Call this FEATURE.

## Step 2: Offer a feature tracker in sparse projects

If `features.md` does **not** exist at the repo root, assess whether this project looks sparse or substantial:
- **Sparse signals**: no `CLAUDE.md`, very few code files, mostly empty repo, or only a `context.md` / brief.
- **Substantial signals**: `CLAUDE.md` exists, established source tree, real commit history.

If the project is sparse, offer once:

> This workflow plays nicely with a simple feature tracker at `features.md` (an In Progress table + Available table). Want me to scaffold one? It's optional — say no and we'll proceed without it.

If accepted, create `features.md` with:

```markdown
# Features

Track what's being worked on and what's queued.

## In Progress

| Feature | Owner | Notes |
|---|---|---|

## Available

| Feature | Notes |
|---|---|
```

Commit just `features.md` with message `Add features tracker`.

If declined, or the project is substantial, proceed without a tracker. Do not raise it again.

## Step 3: Detect state

Look at what exists for this feature:

```bash
ls docs/features/$FEATURE/ 2>/dev/null
```

If `features.md` exists, note whether the feature is claimed and by whom.

## Step 4: Route

Based on what exists, route to the appropriate sub-skill:

| State | Sub-skill |
|-------|-----------|
| No `docs/features/<FEATURE>/requirements.md` | `feature-requirements` |
| Has `requirements.md`, no `plan.md` | `feature-plan` |
| Has `plan.md` with unchecked `- [ ]` items | `feature-implement` |
| All plan items checked, on a feature branch | `feature-review` |

To check for unchecked phases:

```bash
grep -c '\- \[ \]' docs/features/$FEATURE/plan.md 2>/dev/null || echo 0
```

**Do NOT use the Skill tool to invoke sub-skills.** All feature sub-skills have
`disable-model-invocation: true`, which blocks Skill tool invocation entirely.
This flag exists because several sub-skills spawn reviewer subagents via the
Agent tool — and subagents cannot themselves spawn subagents, so these skills
must always run in the main conversation context, never as a nested invocation.

Instead:
1. Tell the user which stage you're routing to and why.
2. Read the sub-skill's instructions from `/home/nigel/.claude/skills/<sub-skill>/SKILL.md`.
3. Execute those instructions inline in this conversation.
