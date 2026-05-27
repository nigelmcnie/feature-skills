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

## Step 3: Read context

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

## Step 4: Draft

Write the requirements document to `docs/features/<FEATURE>/requirements.md`
with the following structure:

- **Problem**: what's broken or missing, with concrete examples.
- **Vision**: one-sentence description of the solved state.
- **User stories**: who benefits and how — every story carries a concrete
  scenario, not just abstract desire.
- **Data model** (if relevant): what's stored and how it relates to the
  existing schema; relationships, not exact column types.
- **Technical approach**: high-level how, not implementation detail.
- **Alternatives considered** (optional): approaches discussed but not
  chosen, with reasoning. Skip the section if the user pre-chose the
  approach and no real alternatives came up — don't fabricate
  alternatives to fill space. Every alternative must be grounded
  (discussed with user, established by a design doc, or an obvious
  known pattern); inline the source.
- **Delivery phases**: ordered increments that each deliver testable
  value; each phase becomes one MR.
- **Indicative implementation notes** (optional, at the bottom):
  plan-level detail worth carrying forward without polluting the
  requirements body — see "Requirements vs plan" below.

### Requirements vs plan

Requirements answer **what** and **why**. The plan answers **how**.

**Belongs in requirements:**
- Problem and desired outcome.
- User-visible behaviour and constraints.
- Data model relationships (that something is stored, not the schema).
- Architectural shape at "we'll do X, not Y" level.
- Why specific tradeoffs were made.

**Belongs in the plan:**
- Function signatures, schemas, exact APIs.
- File paths and module structure.
- Order of operations, phases, test coverage.
- Code-level patterns and snippets.

When in doubt, keep requirements abstract. If a piece of plan-level
detail feels too important to lose, put it in **Indicative
implementation notes** at the bottom of `requirements.md`. The plan
skill reads this section to carry forward useful context.

### Tradeoff guidance

- Prefer simplicity over flexibility. Build for the current need.
- Prefer extending existing patterns over introducing new abstractions.
- Privacy and security are constraints, not afterthoughts. Flag anything
  that stores user data or crosses trust boundaries.
- You can propose deferring part of a feature — either as a later phase
  or as a new entry in the feature tracker. Not everything needs to be
  in scope.

## Step 5: Present and review in parallel

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

## Step 6: Produce feedback synthesis document

For each piece of reviewer feedback, decide your take:

- **My take** should say whether you agree or disagree with reasoning —
  if agreeing, note how you'd address it; if disagreeing, explain why
  the requirement is correct as written.
- For feedback flagging plan-level detail in the requirements, the
  options are:
  1. **Accept and remove**: it's not load-bearing context
  2. **Move to Indicative implementation notes**: useful for planning,
     but doesn't belong in the requirements body (see "Requirements vs
     plan" in Step 4)
  3. **Disagree**: it's genuinely a requirement constraint, not a plan
     choice

### Write the HTML synthesis doc

Use `~/.claude/skills/feature/feedback-template.html` as the basis.
Copy its CSS and JavaScript verbatim. Render the items into the
template's three-tier structure (Needs your input / Feedback / Routine).

Write to `~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements-feedback-<N>.html`,
where `<PROJECT>` is `basename $(git rev-parse --show-toplevel)`.
Create parent dirs with `mkdir -p` if needed.

Update in the template:
- `<title>`, the `<h1>`, the subtitle
- The meta line (item counts)
- The textarea total in the footer
- The JS `docId` constant — e.g. `docs/features/<FEATURE>/requirements-feedback-1`

### Open it

Open the HTML in the user's browser:

```bash
google-chrome ~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements-feedback-<N>.html &
```

The trailing `&` backgrounds the browser process so the agent doesn't wait.

### Hand off

Tell the user the synthesis doc is open and that you'll wait for them
to click **Copy responses** in the HTML and paste the JSON blob back.

## Step 6b: Integrate feedback

The user clicks **Copy responses** in the HTML and pastes a JSON blob
in chat. Format:

```json
{
  "doc": "docs/features/<FEATURE>/requirements-feedback-<N>",
  "responses": { "1": "user text or empty string", ... },
  "routine_flags": { "19": "comment", ... }
}
```

- Empty string in `responses` = agree with your take on that item.
- Non-empty string = user direction; use it.
- Items in `routine_flags` are routine items the user wants to discuss
  — their comment explains why. Treat as needing your call.

If the user signals completion without pasting a blob (e.g. "i'm done"),
ask them to click **Copy responses** in the HTML and paste it.

Integrate all feedback into the requirements document, noting any
declined suggestions inline near the relevant section.

Before archiving the synthesis doc, capture decisions that would
otherwise be lost: check user annotations for design principles, broader
reasoning, or open questions beyond the specific decision. Distill these
into a "Design notes" section in the feature's `requirements.md` (create
it if it doesn't exist). Keep entries to one or two lines, cite the
source review round. Ensure declined suggestions land in "Alternatives
considered" or "Non-goals" with the user's reasoning. Don't duplicate
what's already captured in the requirements text.

Archive the HTML synthesis doc:

```bash
PROJECT=$(basename $(git rev-parse --show-toplevel))
mkdir -p ~/.claude/feature-docs/$PROJECT/<FEATURE>/.feedback-archive
mv ~/.claude/feature-docs/$PROJECT/<FEATURE>/requirements-feedback-<N>.html \
   ~/.claude/feature-docs/$PROJECT/<FEATURE>/.feedback-archive/
```

Remove any resolved inline notes from `requirements.md` once decisions are
captured. Summarise the changes to the user.

## Step 7: Iterate

If the user adds inline notes directly to the requirements document and asks you to
integrate them, or asks to go around the loop again:
1. Re-read the document to pick up their edits
2. Incorporate inline notes into the document properly
3. Re-spawn the reviewer subagent on the updated content
4. Produce a new synthesis document (`requirements-feedback-2.md`, etc.) using the same
   format as Step 6
5. Follow the same fill-in → integrate flow

Repeat as many times as the user wants. The user signals approval conversationally
("looks good", "approved", "let's plan").

## Step 8: Handoff

When the user signals approval — any of: "looks good", "approved", "let's plan",
"ready to plan", "move on", "time to plan", or similar:

1. Check for any remaining `requirements-feedback-N.md` files. If found, integrate
   them (per Step 6b, including capturing design notes) before proceeding.
2. Commit `docs/features/<FEATURE>/requirements.md` with the message
   `docs(<FEATURE>): add requirements` and push.
3. Automatically invoke `/feature-plan <FEATURE>` without waiting to be asked.
