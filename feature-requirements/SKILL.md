---
name: feature-requirements
description: Draft and review requirements for a feature. Use when starting work on a new feature, when the user describes something they want to build, or when there is no requirements.md yet for a feature they want to implement.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
argument-hint: "[feature-name]"
---

# Requirements Workflow

You are starting the requirements phase for a feature.

## Model check

Check your system context for the model you are running on. If your model name does not contain "opus", warn the user:

> ⚠️ This skill expects Claude Opus. You appear to be on [model name]. Opus is recommended here for stronger reasoning during requirements work. Continue anyway?

Wait for their response. If they say no, stop here.

## Branch check

Requirements and plan documents commit directly to main (the project's
default branch) so that implementation phase branches — which fork from
main — have the docs they need to reference.

Check the current branch:

```bash
git branch --show-current
```

- **On `main`** (or the project's default branch): run `git pull` to
  catch up, then proceed.
- **On any other branch**: stop and tell the user. Ask whether to switch
  to main, or whether this project uses a different doc convention.

Do not silently switch branches — uncommitted work might be lost.

## Step 1: Establish the feature name

If `$ARGUMENTS` names a feature from the Available section of `features.md`
(if the project has one), read its description and use `$ARGUMENTS` as the
feature name. If `$ARGUMENTS` is empty or names something not in the tracker,
ask the user to describe what they want in a few sentences. In either case,
confirm the feature name with the user before proceeding. Store this
confirmed name — call it FEATURE — and use it for all file paths. Do not
use `$ARGUMENTS` directly in paths in case the user confirms a different name.

Once FEATURE is confirmed, tell the user:

> → Run `/rename <FEATURE>` to name this session for the feature.

## Step 2: Claim the feature (if a tracker exists)

If `features.md` exists at the repo root, update it: move the feature to the
In Progress table (or add a new row) with the user's name as Owner. Ask the
user for their name if you don't know it. Stage and commit only `features.md`
with the message `Claim <FEATURE> in features.md`, then push — so others
can see it's being worked on.

If there is no `features.md`, skip this step.

## Step 3: Load the brief

Check for a project override at `docs/feature-skill-briefs/requirements.md`
and read it if it exists. Otherwise, read the bundled brief at `brief.md`
in this skill's directory.

## Step 4: Read context

Read the following:
- `CLAUDE.md` (architecture and conventions)
- Any spec or design doc the user has pointed to, including anything linked
  from `features.md` for this feature
- `docs/features/<FEATURE>/context.md` if it exists — treat this as historical
  background context to inform the requirements, not as a spec to transcribe.
  The requirements document should be written fresh, drawing on this context
  where relevant but not constrained by it.
- Any other design docs in the repo that look relevant to the feature.
  Don't restrict yourself to the repo root — explore anywhere that may help.

## Step 5: Draft

Write the requirements document to `docs/features/<FEATURE>/requirements.md`.

Follow the structure and guidance in the brief.

## Step 6: Present and review in parallel

Tell the user the draft is ready for their review. Spawn a reviewer subagent
using the Agent tool with `run_in_background: true` so it runs while the
human reads. Tell the user the reviewer is running and they can start reading
immediately.

Prompt for the reviewer:

> You are reviewing a requirements document for a feature.
> Read the document at `docs/features/<FEATURE>/requirements.md`.
> Read `CLAUDE.md` for architectural context.
> Read any other design docs in the repo that look relevant.
>
> Produce structured feedback covering:
> - What's clear and strong
> - What's ambiguous (needs clarification before implementation)
> - What's missing (gaps a reader would notice)
> - What's over-specified for a requirements doc (belongs in the plan)
> - Strengths and weaknesses of proposed approaches
> - Missed opportunities or alternative approaches
>
> Be specific. Reference sections by name. Focus on substance, not style.

## Step 7: Produce feedback synthesis document

When the reviewer returns, create `docs/features/<FEATURE>/requirements-feedback-1.md`.

Follow the format and triage guidance in
`/home/nigel/.claude/skills/feature/feedback-template.md`. For each piece
of reviewer feedback, **My take** should say whether you agree or disagree
with reasoning — if agreeing, note how you'd address it; if disagreeing,
explain why the requirement is correct as written.

For feedback flagging plan-level detail in the requirements, the options are:
1. **Accept and remove**: it's not load-bearing context
2. **Move to Indicative implementation notes**: useful for planning, but doesn't belong in the requirements body (see the brief's "Requirements vs plan" section)
3. **Disagree**: it's genuinely a requirement constraint, not a plan choice

Tell the user the synthesis document is ready and ask them to fill in their
thoughts on items in the **Needs your input** and **Feedback** sections.

## Step 7b: Integrate feedback

Once the user indicates they are done, re-read both the synthesis document and the
requirements document (to pick up any inline `note: ...` annotations they may have added
directly). Integrate all feedback:
- Blank "Your thoughts" = implicit agreement with your take — proceed accordingly
- Filled "Your thoughts" = use the user's direction, noting any declined suggestions
  inline near the relevant section

Before removing the synthesis document, capture decisions that would otherwise be lost:
check user annotations for design principles, broader reasoning, or open questions beyond
the specific decision. Distill these into a "Design notes" section in the feature's
`requirements.md` (create it if it doesn't exist). Keep entries to one or two lines,
cite the source review round. Ensure declined suggestions land in "Alternatives considered"
or "Non-goals" with the user's reasoning. Don't duplicate what's already captured in the
requirements text.

Archive the synthesis document instead of deleting it (preserves a record
for later analysis):

```bash
mkdir -p docs/features/<FEATURE>/.feedback-archive
mv docs/features/<FEATURE>/requirements-feedback-<N>.md \
   docs/features/<FEATURE>/.feedback-archive/
```

Ensure the archive directory is gitignored locally (not committed). Append
the pattern to the repo's local exclude file if it's not already there:

```bash
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
[ -n "$GIT_DIR" ] && \
  ! grep -qxF '**/.feedback-archive/' "$GIT_DIR/info/exclude" 2>/dev/null && \
  echo '**/.feedback-archive/' >> "$GIT_DIR/info/exclude"
```

Remove any resolved inline notes from `requirements.md` once decisions are
captured. Summarise the changes to the user.

## Step 8: Iterate

If the user adds inline notes directly to the requirements document and asks you to
integrate them, or asks to go around the loop again:
1. Re-read the document to pick up their edits
2. Incorporate inline notes into the document properly
3. Re-spawn the reviewer subagent on the updated content
4. Produce a new synthesis document (`requirements-feedback-2.md`, etc.) using the same
   format as step 7
5. Follow the same fill-in → integrate flow

Repeat as many times as the user wants. The user signals approval conversationally
("looks good", "approved", "let's plan").

## Step 9: Handoff

When the user signals approval — any of: "looks good", "approved", "let's plan",
"ready to plan", "move on", "time to plan", or similar:

1. Check for any remaining `requirements-feedback-N.md` files. If found, integrate
   them (per Step 7b, including capturing design notes) before proceeding.
2. Commit `docs/features/<FEATURE>/requirements.md` with the message
   `docs(<FEATURE>): add requirements` and push.
3. Automatically invoke `/feature-plan <FEATURE>` without waiting to be asked.
