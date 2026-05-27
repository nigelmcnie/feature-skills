---
name: feature-context
description: "Capture a feature idea for later — write docs/features/<name>/context.md and add an entry to the Available section of features.md. Use when the user wants to stash an idea that's emerged from the current conversation. Common trigger phrases include \"let's capture a feature for this\", \"write a context.md for a new feature\", \"add a feature for X\", \"let's get a feature/context up for Y\", \"stash this as a feature\", \"put it in the available features\", \"queue this up as a feature\", and \"we should track this as a feature for later\"."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
argument-hint: "[feature-name]"
---

# Feature Context Workflow

You are capturing background context for a feature that may be worked on later.
This is the historical ledger a future requirements session will draw on — not
requirements itself.

The primary source of context is the **current conversation**: distill what's
been discussed into the structure outlined in Step 3.

## Step 1: Establish the feature name

Pick a short kebab-case name and proceed. Don't ask for permission to
invoke this skill — the trigger language already gave it. Don't bikeshed
the name.

Sources, in order of preference:

1. If `$ARGUMENTS` is provided, use it verbatim.
2. Otherwise, pick a name from the conversation. The clearer the user's
   ask, the less you should hesitate.
3. Only if the conversation truly doesn't make a name obvious (rare),
   ask for the name once — and only the name; don't ask whether to proceed.

If the name turns out to be wrong, the user can rename the directory or
the `features.md` row after — it's cheap to fix. Don't pre-validate by
asking.

Store the chosen name as FEATURE. Mention the name in your "done" message
at Step 6 so the user knows what you chose.

## Step 2: Read context

Read:
- `CLAUDE.md` (architecture and conventions)
- `features.md` if the project has one — to see what already exists and
  avoid duplicating
- Any specific docs the user has pointed to in the conversation

## Step 3: Draft context.md

Write `docs/features/<FEATURE>/context.md` with the following structure:

- **Problem space and motivation**: why this might be worth doing, what's
  broken or missing, what conversations or observations triggered it.
- **Related work**: existing patterns or features in the codebase that
  connect to this; link to other `context.md` / `requirements.md` when
  relevant.
- **Constraints and considerations**: what to watch for, dependencies,
  prior decisions that shape the space.
- **Links**: design docs, customer reports, Slack threads, tickets,
  external references.
- **Open questions**: things worth resolving when requirements get
  written.

Primary source is the recent conversation. Distill — do not transcribe. If the
user discussed a problem, the rationale for solving it, related work, or
constraints, those go in. Conversational filler does not.

Context is not requirements: keep user stories, technical approaches, phase
breakdowns, and wishlist features out. Capture *why* this came up, not just
*what* was discussed. Acknowledge unknowns — a clear "open question" beats
a half-formed guess.

## Step 4: Update features.md (if it exists)

If `features.md` exists at the repo root, add a row to the **Available** table
with the feature name and a brief one-line note. Do not move anything to In
Progress — this feature is being captured for later, not started now.

If `features.md` does not exist, skip this step silently. Do not offer to
scaffold it — that's a separate concern.

## Step 5: Commit and push

Commit `docs/features/<FEATURE>/context.md` (and `features.md` if updated)
with the message `docs: capture <FEATURE> context` and push.

## Step 6: Done

Tell the user the context is captured and that `/feature <FEATURE>` will pick
it up when they're ready to work on it. Then return to whatever the
conversation was doing before.
