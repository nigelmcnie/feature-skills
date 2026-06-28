---
name: feature-agent
description: "Launch a new herdr agent in its own tab to work on a feature-workflow step. Use when the developer asks to \"start <feature>\", \"begin <feature>\", \"let's do <feature>\" or otherwise names a feature to start with no \"in this session\"/\"here\" qualifier (a bare start/begin still means spin up the orchestrator, not run inline), as well as the explicit forms \"start working on <feature> in a new agent\", \"start a new agent on requirements/plan/implement/review for <feature>\", \"kick off <feature> in a fresh tab\", \"spin up an agent to do the plan for <feature>\", \"hand <feature> to a new agent\", or any phrasing that means \"open a new tab and task an agent with a /feature step\". This is the feature-aware launcher; it composes the generic herd-new skill with the right /feature command and model."
allowed-tools: Bash, Read
argument-hint: "[feature-name] [step]"
---

# feature-agent

> **Optional herdr integration, not a core feature skill.** This binds the
> feature workflow to the [herdr](https://github.com/) agent fleet and its
> `herd-new` launcher, the same way
> [`handoff-protocol-example-herdr.md`](handoff-protocol-example-herdr.md)
> binds the neutral handoff payloads. It depends on `herd-new` being on `PATH`.
> Without herdr you don't install it; the workflow stays fully manual.

A developer running the feature workflow under herdr acts as an
**orchestrator**: each feature step (requirements, plan, implement, review,
retro) runs in its own agent in its own tab. This skill is how you launch one of
those agents when the developer asks for it in natural language — it works out
the right `/feature` command and model, then drives `herd-new` to open the tab
and hand off the task.

It is deliberately thin: it does **not** re-implement step resolution. If the
developer doesn't name a step, you hand the new agent `/feature <name>` and let
that router resolve the stage in-session.

## What to resolve before launching

1. **Feature name** — from the request (e.g. "requirements for `api-coherence`"
   → `api-coherence`). If genuinely unclear, ask; don't guess.

2. **The command to hand off:**
   - If the developer **names a step**, use that step's skill:
     | Said | Command |
     |---|---|
     | requirements | `/feature-requirements <name>` |
     | plan | `/feature-plan <name>` |
     | implement | `/feature-implement <name>` |
     | review | `/feature-review <name>` |
     | retro | `/feature-retro <name>` |
   - If the developer **doesn't name a step** ("start working on `<name>`"),
     hand off `/feature <name>` — the router figures out the next stage itself.

3. **Model** (`HERDNEW_MODEL`):
   - `implement` → `sonnet` (the implementer runs on Sonnet).
   - **everything else, and the generic `/feature <name>` router case** → `opus`
     (requirements / plan / review / retro are Opus work).
   - Note the one gap: the generic router case is launched on Opus even though
     the router *might* land on implement (which wants Sonnet). In practice
     "implement" is named explicitly (or comes from a handoff that names it), so
     Opus is the right default. If you know it's implement, treat it as a named
     implement step so it gets Sonnet.

4. **Workspace** (`HERDNEW_SPACE`) — the feature's project repo. Default to the
   current repo's toplevel (`git rev-parse --show-toplevel`). If you're not in
   that project's repo, resolve/ask for the right path; never default to a
   random dir.

5. **Name** (`HERDNEW_NAME`) — **equal to the feature name.** One agent per
   feature; the tab is labelled by the feature.

## Launching

Set the vars and run `herd-new` (see the `herd-new` skill for the full
contract). Background by default — don't steal the developer's focus. Example,
"start a new agent on the plan for `api-coherence`":

```bash
HERDNEW_BACKGROUND=1 \
HERDNEW_HOST="$(hostname -s)" \
HERDNEW_SPACE="$(git rev-parse --show-toplevel)" \
HERDNEW_NAME="api-coherence" \
HERDNEW_MODEL="opus" \
HERDNEW_PROMPT="/feature-plan api-coherence" \
herd-new
```

Generic case ("start working on `api-coherence` in a new agent") — same, but
`HERDNEW_PROMPT="/feature api-coherence"` and `HERDNEW_MODEL="opus"`.

## How to behave

- **Announce before launching** — one line: feature, step (or "router"),
  model, background. e.g. *"Launching a background agent `api-coherence` on
  Opus, tasked with `/feature-plan api-coherence`."*
- **After launch, tell the developer** the task you handed it and that the step
  skills are interactive (requirements/plan/review interview *them*), so that
  tab will be waiting on their input. They reach it by name via `Ctrl+G` or the
  picker.
- **One agent per feature.** Re-running with the same name adds another tab; it
  doesn't reattach. If an agent for the feature is already up and idle, wake it
  instead (`herdr agent send <feature>` + an Enter keystroke — see `herd-new`),
  rather than spawning a duplicate.

## Relationship to the agent-handoff flow

This skill is the **manual entry point** to the same launch action that a
handoff binding (see `handoff-protocol-example-herdr.md`) performs
**automatically** when it acts on an `agent-handoff` payload (a finished step
declaring the next one). Both end in "open a tab, pick the model, type a
`/feature` command" — so when acting on a handoff, use this skill's
command/model/naming rules so the two paths stay consistent. The feature skills
themselves stay herdr-free; this coupling lives only in the developer's
environment configuration plus this optional skill.
