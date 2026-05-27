---
name: feature-plan
description: Create an implementation plan for a feature with approved requirements. Use after requirements are approved, when the user says it's time to plan, or when there is a requirements.md but no plan.md yet for a feature they want to implement.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
argument-hint: "[feature-name]"
---

# Planning Workflow

You are creating an implementation plan for a feature whose requirements
have been approved.

## Model check

Check your system context for the model you are running on. If your model name does not contain "opus", warn the user:

> ⚠️ This skill expects Claude Opus. You appear to be on [model name]. Opus is recommended here for stronger reasoning during planning. Continue anyway?

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

## Step 1: Read context

Read the following files:
- `docs/features/$ARGUMENTS/requirements.md` (approved requirements) —
  including any **Indicative implementation notes** section at the bottom,
  which carries forward plan-level context that didn't belong in the
  requirements body
- `CLAUDE.md` (architecture and conventions)
- All source modules referenced in the requirements' technical approach
- Existing test files to understand testing patterns

## Step 2: Draft

Plans are produced in **two formats** during Phase 2A. Markdown is
canonical (committed to the repo, source of truth for the workflow,
read by the implementing agent). HTML is the rich review surface.

### Plan structure

A good implementation plan contains:

- **Overview**: what we're building, in one paragraph.
- **Key technical decisions**: choices that shape the implementation,
  with rationale. Include code snippets showing key interfaces.
- **File structure**: what files are created or modified.
- **Phase breakdown**: for each delivery phase from the requirements:
  - What's built
  - Which files are touched
  - Key code snippets (interfaces, data structures, function signatures)
  - What tests are needed
  - MR chain (each phase = one MR, invoked separately)
- **Checklist**: a flat checklist of all steps across all phases at the
  bottom of the document. The implementing agent checks items off as
  it works.

### Detail level

The plan should be detailed enough that an implementing agent (which
may be a different, less capable model) can follow it without making
significant design decisions. Include:

- Function signatures with type hints.
- Schema changes.
- Key conditional logic ("if X, then Y; otherwise Z").
- Test descriptions (what's tested, not full test code).

Do NOT include:

- Full implementation code (that's the implementing agent's job).
- Exact line numbers (files change).
- Style decisions (formatter handles them).

### Phasing

- Each phase results in a separate MR.
- Each phase is independently testable.
- Each phase is implemented by a separate invocation of
  `/feature-implement`.
- The implementing agent checks off items in this plan as it works.
- The plan is a living document — it gets updated if the approach
  changes during implementation. If a deviation is significant, pause
  and get the human to review the revised plan before continuing.

### Checklist format

The flat checklist at the bottom **must** use phase headers so the
implementing agent can identify phase boundaries unambiguously:

```markdown
## Checklist

### Phase 1: <name>
- [ ] Step A
- [ ] Step B

### Phase 2: <name>
- [ ] Step C
- [ ] Step D
```

Items within each phase are ordered as they will be implemented.

### Quality control

Reference `CLAUDE.md` for quality control steps rather than hardcoding
them. Instruct the implementing agent to follow whatever `CLAUDE.md`
says at implementation time.

### Pass 1 — Write the markdown plan

Write to `docs/features/$ARGUMENTS/plan.md`, following the structure
and detail-level guidance above. Include:

- Key technical decisions with code snippets
- File structure showing what's created/modified
- Phase breakdown with test descriptions and MR chain
- Flat checklist of all steps at the bottom

### Pass 2 — Render the HTML plan

Use `~/.claude/skills/feature/plan-template.html` as the basis. Copy its
CSS and JavaScript verbatim. Render the markdown plan into the template's
structure: TOC sidebar, sections per the markdown's headings, syntax-
highlighted code blocks, phase badges, clickable checklist, click-to-
comment widget, sticky footer.

Write to `~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html`, where
`<PROJECT>` is `basename $(git rev-parse --show-toplevel)`. Create
parent dirs with `mkdir -p` if needed.

Update in the template:
- `<title>`, the `<h1>` (feature name), the subtitle
- The TOC entries to match the actual sections in the plan (use `id`
  attributes on each `<section>` that match the TOC's `href` anchors)
- The JS `docId` constant — e.g. `docs/features/<FEATURE>/plan`

### Open it

Open the HTML in the user's browser:

```bash
google-chrome ~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html &
```

The trailing `&` backgrounds the browser process so the agent doesn't wait.

## Step 3: Present and review in parallel

Tell the user the plan is ready for their review. Spawn a reviewer subagent
using the Agent tool with `run_in_background: true` so it runs while the
human reads. Tell the user the reviewer is running and they can start reading
immediately.

Prompt for the reviewer:

> You are reviewing an implementation plan for a feature.
> Read the plan at `docs/features/$ARGUMENTS/plan.md`.
> Read the requirements at `docs/features/$ARGUMENTS/requirements.md`.
> Read `CLAUDE.md` for architectural context.
>
> Check:
> - Does the plan cover all requirements? Flag any gaps.
> - Are the file paths correct? Do the modules exist?
> - Does it account for cross-cutting concerns called out in `CLAUDE.md`?
> - Are there dependency issues or blockers?
> - Is the phasing sensible? Can each phase be independently tested?
> - Are the code snippets consistent with existing patterns?
>
> Be specific. Reference sections by name.

## Step 4: Process reviewer feedback inline

When the reviewer returns, triage each item into one of:

- **Apply** — you agree with the reviewer, and the change is uncontroversial:
  factual corrections, missed dependencies, citation/path fixes, polish,
  wording. These get applied directly without asking.
- **Ask** — the item involves a real decision: product semantics, naming
  for concepts, scope or phasing trade-offs, deferral decisions, anything
  strategic. Surface inline with your take.
- **Skip** — you disagree with the reviewer or it's already covered.
  Briefly say why.

Present the triage in chat — do not write a synthesis document. Format:

> Reviewer feedback for plan:
>
> **Will apply:**
> - <one-line description>
> - ...
>
> **Will skip:**
> - <one-line description + brief reason>
> - ...
>
> **Need your call:**
> 1. <Question>. My take: <brief>.
> 2. <Question>. My take: <brief>.
>
> Reply with answers (or "go" to take my take on all of them) and I'll apply.

The user may also leave click-to-comment annotations in `plan.html` and
paste a JSON blob back. Format:

```json
{
  "doc": "docs/features/<FEATURE>/plan",
  "comments": [
    {"excerpt": "...", "text": "user comment"}
  ]
}
```

Fold those comments into the same triage — each comment is an additional
piece of feedback. The user may paste comments alongside the reviewer's
output, before it, or independently.

Wait for the user's response. Apply the "Will apply" items plus the
resolved questions and any actionable comment annotations.

If any "Need your call" answers reveal substantive design decisions
(principles, reasoning, broader implications beyond the specific item),
capture them in a "Design notes" section of
`docs/features/<FEATURE>/requirements.md`. Keep entries to one or two
lines, cite the review round.

After applying changes to `plan.md`, **re-render the HTML** (Step 2 Pass 2)
to keep `plan.html` in sync. The user may want to reload it.

Summarise what was applied to the user.

## Step 5: Iterate

If the user provides further feedback via any of:
- Inline `note: ...` annotations in `plan.md`
- Click-to-comment JSON pasted from `plan.html`
- Direct chat instructions

Then:
1. Re-read `plan.md` to pick up any inline edits
2. Apply the new feedback to `plan.md`
3. Re-render `plan.html` from the updated markdown
4. (If the changes are substantial) re-spawn the reviewer subagent on the
   updated content
5. Follow Step 4 (triage and process inline) for any new reviewer feedback

Repeat until the user approves conversationally.

## Step 6: Handoff

When the user signals approval — any of: "looks good", "approved", "let's
implement", "ready to implement", "start building", "time to implement", or
similar:

1. Check for any remaining `plan-feedback-N.md` files. If found, integrate
   them (per Step 4) before proceeding.
2. Commit `docs/features/<FEATURE>/plan.md` and `docs/features/<FEATURE>/requirements.md`
   (the latter may have been updated with design notes) with the message
   `docs(<FEATURE>): add implementation plan` and push.
3. Tell the user:

   > Plan approved. When you're ready to implement, switch to your Sonnet session and run:
   >
   > `/feature-implement <FEATURE>`

Do not invoke `/feature-implement` yourself.
