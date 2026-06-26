# Handoff protocol

The workflow moves between stages that may run on different models, in
different sessions, sometimes across an external gate (an MR merging). A
stage never says *how* the next stage starts — only *what* should happen.
Two payload types carry that intent. The environment supplies how they're
acted on; with nothing supplied, each has a fallback that addresses the
developer directly — the default, fully manual behaviour.

The skill never assumes a mechanism exists, never names one, and never
describes its shape. It only produces the payload.

## Acting on a payload

Check whether your environment defines an **agent-handoff** convention (for
example, in your environment/CLAUDE.md):

- **Defined** → hand it the payload.
- **Not defined** → render the payload's fallback to the developer as prose,
  and stop.

Whatever acts on a payload **must read its `notes` field (where present) and
weigh it before acting** — it may change what the safe checks do, what's
surfaced to the developer, or whether to proceed at all.

## `agent-handoff` — the next stage to run

- `command` — slash command, e.g. `/feature-implement <FEATURE>`
- `model` — model that stage expects (from its Model check): Opus | Sonnet
- `when` — `now` (a human gate already passed) | `after-merge:<mr-ref>`

**Fallback rendering:**

- `now` → "When you're ready, switch to your \<model> session and run
  `<command>`."
- `after-merge:<ref>` → "Once \<ref> has merged, run `<command>` (on
  \<model>)."

Always preserved: the current session does **not** invoke `command` itself
when `model` differs from the current model, or when `when` is not `now`.

## `phase-report` — emitted by `/feature-implement` at each phase boundary

Carries everything that must cross the merge gate, so it survives the
implementing session going idle or closing.

- `status` — `phase-complete` (more phases remain) | `all-complete`
- `mr` — MR reference for the phase just pushed
- `post_merge[]` — checks to run after merge, each tagged:
  - `safe` — non-destructive / reversible; may be run automatically on main
    (pull/reinstall/restart, reversible migration, re-index)
  - `human` — only a person can do it; carries a link/command + expected
    outcome + any dashboard/channel
- `verify_flags[]` — "Verify" checklist items that couldn't be confirmed
  live (implement Step 2.5): the constraint + a structural equivalent if one
  exists
- `notes` — freeform. Anything the implementer judges worth reporting that
  doesn't fit the fields above: plan deviations, surprises, partial
  concerns, judgement calls, things the next stage should watch. The
  emitter is encouraged to use it; a receiver **must** consider it (see
  *Acting on a payload*).
- `next` —
  - `phase-complete` → the **same** implementer resumes the next phase after
    `mr` merges (a wake, not a new handoff)
  - `all-complete` → an `agent-handoff`: `/feature-review <FEATURE>`, model
    Opus, `when: after-merge:<mr>`

**Fallback rendering** (this is exactly today's implement Step 7 + Step 2.5):

- Run the `safe` checks yourself now where live state allows; list the
  `human` ones for the developer to do after merge, with links and expected
  outcomes.
- State any `verify_flags` as requiring manual verification post-merge.
- Surface anything in `notes` to the developer.
- `phase-complete` → tell the developer to say "next phase"/"continue" once
  `mr` merges; confirm the merge before resuming.
- `all-complete` → render the attached `agent-handoff`.
