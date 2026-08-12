---
name: feature-mr-feedback
description: Triage and respond to native platform review comments (automated bot findings and human replies) on an already-open, not-yet-merged feature-phase MR/PR. Use when the user says there's review feedback on a specific open MR/PR to address. Distinct from feature-iterate, which handles the feature-skills synthesis-driven review loop after a full feature has already merged.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
argument-hint: "[feature-name] [mr-or-pr-reference]"
---

# MR Feedback Workflow

You are triaging and responding to review feedback that has landed
natively on the platform (GitLab/GitHub) — a bot, a human, or both — on
an **already-open, not-yet-merged** MR/PR for one phase of a feature.

**This is not `/feature-iterate`.** `feature-iterate` addresses feedback
from the feature-skills synthesis pipeline (`/feature-review`'s tiered
triage doc) after the *entire feature* has merged to main, and lands its
fix on a fresh `features/<FEATURE>-iterate-N` branch with its own MR.
This skill instead reacts to comments the platform itself surfaced on a
*single phase's MR that hasn't merged yet* — most often an automated
reviewer bot, sometimes with the developer's own reply already on the
thread — and pushes the fix to that **same** branch, landing on the
**same** MR. No synthesis doc, no new branch, no re-review subagent.

This can run at any point after `/feature-implement` created the MR —
including long after that session went idle or ended. Nothing here
assumes the phase's worktree still exists.

Unlike its sibling feature skills, this one has no `disable-model-invocation`
— it never spawns a subagent (no step here uses the Agent tool), so there's
no risk of the subagent-spawning-a-subagent problem that flag exists to
prevent. Plain language matching the description above (e.g. "there's
feedback on the MR, go handle it") should trigger it directly.

## Model check

Check your system context for the model you are running on. If your model name does not contain "sonnet", warn the user:

> ⚠️ This skill expects Claude Sonnet. You appear to be on [model name]. Sonnet is recommended here — this is implementation-style work reacting to specific feedback, and doesn't need Opus-level reasoning. Continue anyway?

Wait for their response. If they say no, stop here.

## Current branch
!`git branch --show-current`

## Step 0: Resolve the feature, the MR, and its branch

Resolve `PROJECT`: `PROJECT=$(basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")")`.

`FEATURE` is the first token of `$ARGUMENTS` if given, else ask the user.

The MR/PR reference is the second token of `$ARGUMENTS` (an IID/number or a
full URL) if given. Otherwise, find it:

- **GitLab**: `glab mr list --source-branch "features/$FEATURE-p*" --state opened`
  (glob won't work directly — list open MRs and match branch names starting
  `features/$FEATURE-p`).
- **GitHub**: `gh pr list --search "head:features/$FEATURE-p" --state open`

If exactly one open MR/PR matches, use it. If several match, list them
(branch, title, URL) and ask which one. If none match, tell the user and
stop — this skill needs a live, open MR/PR to act on.

Note the MR/PR's source branch name (e.g. `features/harden-settlement-crons-p2`)
— you'll need it in Step 1.

## Step 1: Get onto the MR's branch, isolated

This is the same worktree convention `/feature-implement` uses, but for an
**existing** branch, not a fresh one — you're resuming work on a branch
that already has commits and an open MR, not starting a phase.

- Check the repo's `CLAUDE.md` (and `.claude/`) for worktree instructions
  first, same as `/feature-implement` Step 1. Most repos with that
  convention provide a **checkout** flow for existing branches (e.g. this
  repo's `wm checkout <branch> --subdir`), distinct from the **create**
  flow used for new phases. Use the checkout flow — it's idempotent, so
  it's safe to call even if a worktree for this branch still exists from
  the original `/feature-implement` session.
- If the repo has no such tool, use `EnterWorktree` with `path=` if a
  worktree for this branch already exists, or create one manually:
  ```bash
  git fetch origin
  git worktree add .claude/worktrees/<name> <branch>
  # then call EnterWorktree with path=.claude/worktrees/<name>
  ```
- Once in the worktree, update from the remote in case commits landed
  elsewhere since — `git fetch origin && git merge --ff-only origin/<branch>`,
  never a bare `git pull` (worktrees are typically shared across agents, and
  `pull`'s rebase can refuse on a dirty index left elsewhere; fetch + ff-merge
  fast-forwards without touching anything else). If the merge isn't a
  fast-forward, stop and tell the user rather than force-merging.
- If worktrees are unavailable (not a git repo, or the user vetoes
  isolation), fall back to `git checkout <branch>` in the current tree and
  tell them you're not isolated.

## Step 2: Fetch the discussion threads

- **GitLab**: `glab api projects/:fullpath/merge_requests/<IID>/discussions`
  — each element is a thread; each note has `author`, `body`, `system`,
  and (for `DiffNote`s) `resolved`/`resolvable`.
- **GitHub**: review comments via `gh api repos/:owner/:repo/pulls/<N>/comments`
  (inline, threaded via `in_reply_to_id`) plus general conversation via
  `gh api repos/:owner/:repo/issues/<N>/comments`. GitHub's REST API
  doesn't expose thread-resolved state as cleanly as GitLab's — treat any
  comment newer than your last pass as needing triage.

Skip threads already marked resolved. For everything else, read every
note in the thread in order — you need the full back-and-forth, not just
the first comment.

## Step 3: Classify each unresolved thread

This is the core judgement call. Default rule (general-purpose; tune per
project or per user instruction if told otherwise):

> **When a thread contains both an automated review comment (a bot) and a
> reply from the developer, the developer's reply is authoritative — it
> outweighs the bot's original finding, every time.** If the developer
> pushed back on or redirected the bot's finding, follow their direction:
> do not action what they've explicitly declined, even if the bot's
> reasoning looks sound in isolation. If the developer endorsed or
> extended the finding, act on that (their version of it, not just the
> bot's original wording).

Beyond that:

- **Bot-only thread** (no developer reply yet): evaluate on its own merits
  like any other review comment — check it against the project's rules/
  docs (`docs/rules/`, `CLAUDE.md`, architecture docs), and decide to act
  or to push back with your own reasoning, replying either way.
- **Developer-only comment** (not replying to a bot, just their own
  observation or request): treat it as a direct instruction. If it's
  exploratory ("try X, and if that doesn't work, try Y") — **verify
  empirically, don't assume**: actually make the change, run the affected
  tests, and report what you found. Don't conclude from reasoning alone
  when the answer is one test run away.
- **Human-only thread from someone other than the developer** (a
  teammate, another reviewer): treat as you would any human reviewer
  comment on your own PRs generally — evaluate on merits, defer to the
  developer only where they've also weighed in on the same thread. The
  developer's stance doesn't have to be a reply posted on the thread itself
  — if they've told you their take in the conversation that invoked this
  skill (e.g. "I agree with Richard, but do X instead"), that counts the
  same as a posted reply for classification purposes: act on their version,
  not the reviewer's original wording.

## Step 4: Act

For each thread that needs a code change:

- Make the change, following the project's usual conventions (`CLAUDE.md`,
  relevant `docs/rules/`).
- For exploratory requests (Step 3), confirm the outcome by actually
  running the relevant tests before drawing a conclusion — mirror
  `/feature-implement` Step 2.5's "verify empirically" standard.
- If a thread's finding turns out to need no change (you're pushing back,
  or the developer already declined it), no code change is needed — just
  prepare your reply for Step 6.

## Step 5: Quality control

Before committing, invoke `/feature-qa` and work through all checks it
defines. **Do NOT use the Skill tool to invoke `/feature-qa`** — it sets
`disable-model-invocation: true`, which blocks the Skill tool. Read
`~/.claude/skills/feature-qa/SKILL.md` and execute its instructions
inline in this conversation.

## Step 6: Commit, push, and reply

- Commit with a message that references what feedback prompted the
  change (e.g. `fix(<feature>): <what>, per review feedback`).
- Push to the **same branch** — this lands on the existing MR/PR, no new
  one is created.
- Reply on every thread you engaged with (acted on, or explicitly decided
  not to), stating the outcome and citing the commit. For exploratory
  requests, report the concrete result (what you tried, what happened),
  not just the conclusion.
- Resolve a thread only when its request has been concretely and fully
  addressed. Leave a bot-vs-developer judgement call you're relaying
  (rather than deciding yourself) open for the developer's own sign-off,
  unless they've told you they're comfortable with you closing those too.

## Step 7: Watch the pipeline

Follow `/feature-implement` Step 6's pipeline-watch process exactly: wait
for the new pipeline to terminate, triage mechanical failures and fix
them (capped at 3 attempts), escalate strategic failures, don't hang past
~15 minutes.

## Step 8: Report back

Before writing the message, check: does this MR carry a known constraint —
a not-ready-to-merge banner, a gate outstanding, a "don't merge yet" the
user stated earlier? If so, **restate it explicitly in this report**, even
if nothing about it changed this round and even within the same session —
it's the easiest thing to drop once the thread-by-thread detail takes over,
and a clean pipeline reads as "ready" if you don't say otherwise.

Then tell the user, concisely:

- Any standing constraint restated per above.
- Which threads were addressed, and how (one line each).
- Which threads are still open and need their own word, and why.
- Final pipeline state, with the MR/PR link.
