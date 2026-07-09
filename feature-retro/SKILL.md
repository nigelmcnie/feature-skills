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

Derive `PROJECT = basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"`
(resolves to the main checkout's name from both the main tree and a leftover
phase worktree — the latter being the normal state right after
`feature-implement` finishes; `--path-format=absolute` matters, because from
the main checkout `--git-common-dir` returns the relative `.git` and without
it `PROJECT` resolves to `.`) and take
`FEATURE` from `$ARGUMENTS` (ask if absent). Then look at:

- Plan: `GET http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1`
  from the webapp. Fall back to
  `~/.claude/feature-docs/$PROJECT/$FEATURE/plan.html` if the API
  returns 404. Compare against what actually shipped.
- Requirements: `GET http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/requirements/1`
  from the webapp. Fall back to
  `~/.claude/feature-docs/$PROJECT/$FEATURE/requirements.html` if the
  API returns 404. Read the "Review decisions" section.
- `.feedback-archive/*.html` under `~/.claude/feature-docs/$PROJECT/$FEATURE/` —
  the synthesis docs from requirements/review rounds. Recurring themes
  across them are gold.
- `~/.claude/feature-docs/$PROJECT/features.html` — the tracker entry.
- The project's prior open retro findings, if the webapp store is
  reachable — see **Recurrence capture** below. Read these before you
  judge this session; they're what lets you recognise a repeat instead
  of re-discovering it.

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
  or feature-skills-webapp. **Discuss it inline — don't spin it into a
  feature-context.** The point is the conversation; the developer decides
  if it's worth pursuing. These discussion-class findings are the ones
  captured to the webapp at retro end (see **Recurrence capture**), so the
  conversation compounds across retros instead of evaporating.

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

### Surfacing calibration (when the webapp is reachable)

The sharpest signal for tuning the "surface only what I care about" dial
is the developer's own past answers. Fetch them via the webapp's HTTP
API — never the DB directly (the project's own convention for this
store: use the API, not the SQLite file). This also means it works from
any machine that can reach the webapp, including over a forwarded port,
not just the one hosting it. List the feature's documents, then pull
each relevant instance's synthesis:

```bash
curl -fsS "http://127.0.0.1:8800/api/projects/$PROJECT/features/$FEATURE/documents" 2>/dev/null
# then, per doc_type/instance that had a synthesis round this cycle:
curl -fsS "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/<doc_type>/<instance>/synthesis" 2>/dev/null
```

Each call returns `responses` and `routine_flags`, keyed by item id — a
non-empty entry means the developer engaged (redirected); an absent or
empty one means they agreed with the take. Tiers aren't in this
response — read them from the synthesis HTML in each feature's
`.feedback-archive/` (the `tier-needs-input` / `tier-feedback` /
`tier-routine` sections), or from the inline "Need your call" vs
"Applying" split that review/plan now use.

For the feature(s) reviewed this cycle, join answers to tiers and flag:

- **Misses** — items the developer redirected that were *not* surfaced as
  a decision (sat in Feedback / Applying). Each is a triage gap: what
  shape did it have that the criteria didn't catch? (Recurring shapes to
  watch: a take that resolved toward deferring/cutting; a deviation from
  the context doc / `CLAUDE.md` / a prior decision; a risk.)
- **Over-surfacing** — decision-tier items the developer left blank
  (agreed). A doc where *everything* surfaced was agreed suggests the
  reviewer escalated too much.
- **Recurring redirect shapes** not yet named in the triage criteria —
  candidates to add (a quick win), or to discuss if larger.

Keep it light when data is thin — a couple of rounds won't support strong
conclusions. This is the calibration loop the workflow is meant to run on
itself.

## Recurrence capture (when the webapp store is available)

Discussion-class findings used to evaporate when the session ended. The
webapp now persists them so each retro can stand on what prior retros
found — the continuous-refinement loop the workflow is built on. The
contract is two HTTP calls against the local webapp
(`http://127.0.0.1:8800`, the same localhost-only store the polling
convention uses). If the server is unreachable or the project isn't known
to the webapp (`404`), skip silently and run the retro exactly as before
— capture is an enhancement, never a blocker.

**At the start — read priors.** Before judging this session, pull the
project's still-open findings:

```bash
curl -fsS "http://127.0.0.1:8800/retro-findings?project=$PROJECT" 2>/dev/null
```

This returns the `open` + `deferred` findings, each with an **`id`**,
`title`, `evidence`, `change`, `feature`, and `recurrence_count`. Read
them as prose — they're prior process observations. Hold onto the `id`s:
a new finding that restates one of these cites it as `recurs_from` on the
post below.

**In session — surface recurrence.** When a finding you're about to raise
restates a prior one, say so inline as you raise it — "this echoes a
finding from `doc-view` two retros ago" — so the developer can weigh it as
a pattern in the moment, not discover the repetition later. A prior
finding already carrying a high `recurrence_count` is a strong signal it's
worth promoting to a tracked feature; flag that explicitly.

**At the end — post the discussion findings.** Post every
*discussion-class* finding (the "Worth a discussion" ones) — **not** quick
wins (they survive in git) and **not** `/retro` items (they persist as
config/memory). Capture is autonomous: post all of them, not only the ones
the developer blessed — you can't tell in the moment which will recur, and
inbox triage plus the recurrence signal keep the noise down, not
pre-filtering here.

Generate a fresh run key per invocation — each retro is its own run, so
the planner's and the implementer's retros on the same feature coexist
rather than overwriting each other:

```bash
RUN_KEY=$(uuidgen 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())')
```

Write the payload to a temp file (keeps JSON escaping sane), POST it, then
remove it. Use `mktemp` for a unique path — a hardcoded `/tmp` name would let
two concurrent retros on the same feature (e.g. the planner's and the
implementer's, the very coexistence the fresh run key is for) clobber each
other's payload mid-write, and would linger in `/tmp` afterward:

```bash
PAYLOAD=$(mktemp /tmp/retro-findings.XXXXXX.json)
# …write the JSON body (below) to "$PAYLOAD"…
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d @"$PAYLOAD" \
  http://127.0.0.1:8800/retro-findings 2>/dev/null || true
rm -f "$PAYLOAD"
```

with a body of:

```json
{ "project": "<PROJECT>",
  "run": { "key": "<RUN_KEY>", "feature": "<FEATURE>", "ran_at": "<date -u +%FT%TZ>" },
  "findings": [
    { "title": "…", "evidence": "…", "change": "…", "recurs_from": <prior id> } ] }
```

`title` is required; `evidence` and `change` mirror your output format.
Set `recurs_from` **only** to an `id` you actually read from the GET above
— a stale, cross-project, or invented id is rejected (`400`); omit the
field entirely for a genuinely new finding.

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

Once you've surfaced the findings, **post the discussion-class ones to
the webapp** per **Recurrence capture** above — automatically, without
waiting to be told which are worth keeping. Then end with a single line:
**"Want me to apply any of the quick wins?"** — and if they pick some, do
them (editing the relevant `SKILL.md` / template). Don't apply any quick
win before they choose, and don't act on the discussion items beyond
talking them through and capturing them.
