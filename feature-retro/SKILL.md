---
name: feature-retro
description: "Retro on how the feature-development *process* went (not the code) and surface concrete ways to streamline the feature-skills workflow itself. Reconstructs a feature's whole arc from its artifacts (requirements, plan, archived feedback, MR history) plus the current session, and judges it against the workflow's direction of travel. Invoke explicitly via /feature-retro, typically at the end of an implement or iterate session. Trigger phrases: \"feature retro\", \"feature-skills retro\", \"retro the process\", \"how did that process go\"."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
argument-hint: "[feature-name]"
---

# Feature Retro

Look back over how the **feature-development process** went for this
feature and surface a small set of concrete improvements to the
**feature-skills workflow itself** — the skills in this repo and the
companion `feature-skills-webapp`. This is about the *process*, not the
code that shipped.

It is distinct from the global `/retro`, which improves Claude's config,
installs, and memory from the current session. Run both at the end of a
session; they don't overlap. **Stay out of `/retro`'s lane** — if a
finding is a CLAUDE.md instruction, a tool to install, a hook, a
permission, or a memory entry, it belongs to `/retro`, not here. Note it
in one line and move on.

## The direction of travel (judge findings against this)

The feature-skills exist so the developer can do spec-driven development
with agents while keeping a close eye on what they're doing — seeing the
requirements are right, understanding the plan, never letting the agent
drift too far. The process has been steadily streamlined as understanding
of agents improved (markdown → HTML; full review → only the decisions
worth caring about; local docs → central store → webapp).

Where it's heading:

- **More of the process proceeds automatically** where the developer's
  involvement isn't necessary — **while always surfacing the decisions
  they want to weigh in on**, and no more.
- **Works everywhere**: solo repos, shared repos where teammates don't
  know the process, across multiple machines (hosted webapp), and
  eventually shared with others at Sharesies.
- **Multiple agents** in play, not the current fixed split.
- The far goal: build a feature by writing the first context, kicking
  off the skill, answering the key questions (and asking a few of your
  own), and otherwise having it move forward.

A good finding moves the process toward that picture. The two richest
veins are **(a) streamlining what currently needs the developer but
shouldn't**, and **(b) tuning the "surface only the decisions I care
about" dial in both directions.**

## What to read

A feature's development spans multiple sessions and models, so the
current session never holds the whole arc. Reconstruct it from the
durable artifacts, then layer the lived friction of this session on top.

Derive `PROJECT = basename "$(git rev-parse --show-toplevel)"` and take
`FEATURE` from `$ARGUMENTS` (ask if absent). Then look at, under
`~/.claude/feature-docs/$PROJECT/$FEATURE/`:

- `plan.html` — the planned phases. Compare against what actually
  shipped.
- `requirements.html` — including the "Review decisions" section.
- `.feedback-archive/*.html` — the synthesis docs from
  requirements/review rounds. Recurring themes across them are gold.
- `~/.claude/feature-docs/$PROJECT/features.html` — the tracker entry.

And in the target repo:

- `git log` for the phase and iterate branches/MRs
  (`features/<feature>-p<N>`, `features/<feature>-iterate-N`). Watch for
  `fix(...): address CI ... failures` commits — repeated ones are a
  friction signal.

Plus the **current session**: where you were asked things, where you
proceeded and got corrected, where steps were manual.

## How to think about it

For each notable moment, ask: **"did this move the process toward the
goal, or away from it — and what concrete change closes the gap?"** A
finding is only worth surfacing if you can name the change and where it
lives (a feature-skills `SKILL.md`/template, or a feature-skills-webapp
capability).

Signals, in priority order:

- **A decision you raised that the developer just rubber-stamped** →
  it could be downgraded to routine or auto-applied. Being asked what
  you didn't need to ask is friction.
- **A place you proceeded and the developer had to course-correct** →
  the inverse: it should have been surfaced as a decision. Both tune
  the "surface only what I care about" dial.
- **A manual step the developer performed** that the workflow could
  own automatically.
- **Friction from the cross-repo / shared-repo / multi-machine /
  multi-agent constraints** → often a feature-skills-webapp candidate.
- **Plan-vs-reality drift** — phases added/cut, scope creep, deferred
  work — and **recurring review themes** → planning or QA-prompt gaps.

Each finding is one of two shapes:

- **Quick win** — a small, confident tweak to a skill or template
  (reword a prompt, move an item between triage tiers, add a step).
  Name the exact file and change; offer to apply it.
- **Larger discussion** — a change to how the process works that's worth
  talking through, and may end as a feature to build in feature-skills
  or feature-skills-webapp. **Discuss it inline — don't capture it as a
  feature-context or write anything.** The point is the conversation;
  the developer decides if it's worth pursuing.

Be selective. Three sharp findings beat ten padded ones. Low
signal-to-noise kills a tool like this. If the process ran clean, say so
plainly — "nothing worth changing this time" is a respectable result.

Decision/knowledge capture (loose decisions that never reached a durable
home) and deferred follow-ups are worth a glance, but they're a light
touch here — the other skills handle them in their normal flow. Don't let
them become the headline.

One concrete cleanup to check directly, even though cleanups are
otherwise `/retro`'s lane: run `git stash list` for stashes created
during this session and never restored. An implement or iterate agent can
stash work mid-feature and forget it; a forgotten stash is easy to lose
and risky to pop blindly later. Flag any for the developer to clear.

## Output format

Group findings under these headings, highest-leverage first. **Omit any
heading with no findings.**

- **Quick wins** — small skill/template tweaks, each with the exact file
  and change
- **Worth a discussion** — larger process changes / feature candidates
  for feature-skills or feature-skills-webapp, talked through inline
- **Loose ends** — leftover session artefacts to clear, especially
  forgotten `git stash` entries
- **For `/retro`** — at most a one-line pointer if you noticed a
  config/install/memory item that's really `/retro`'s job

For each finding:

> **<short title>** — what happened this feature (the evidence, 1
> sentence), and how it relates to the direction of travel. → **Change**:
> the concrete tweak and where it lives, or the question worth discussing.

Keep each to two or three lines. Cite the moment so the developer can
judge it fast.

End with a single line: **"Want me to apply any of the quick wins?"** —
and if they pick some, do them (editing the relevant `SKILL.md` /
template). Don't apply anything before they choose, and don't act on the
discussion items beyond talking them through.
