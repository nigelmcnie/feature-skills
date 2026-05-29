---
name: feature-requirements
description: Draft and review requirements for a feature. Writes the canonical requirements.html to the developer-scoped store and optionally exports markdown/HTML to the repo via .feature-workflow.toml. Use when starting work on a new feature, when the user describes something they want to build, or when there is no requirements doc yet for a feature they want to implement.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
argument-hint: "[feature-name]"
---

# Requirements Workflow

You are starting the requirements phase for a feature.

The canonical requirements doc is HTML in the developer-scoped store at
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html`, where
`<PROJECT>` is `basename $(git rev-parse --show-toplevel)`. The repo
gets an exported snapshot (markdown or HTML) when `.feature-workflow.toml`
opts in.

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

Also resolve PROJECT once and reuse it everywhere:

```bash
PROJECT=$(basename $(git rev-parse --show-toplevel))
```

Once FEATURE is confirmed, tell the user:

> → Run `/rename <FEATURE>` to name this session for the feature.

## Step 2: Claim the feature (if a tracker exists)

The canonical tracker is
`~/.claude/feature-docs/<PROJECT>/features.html`. The repo's
`features.md` (if any) is a script-generated snapshot when
`.feature-workflow.toml` opts in.

### Ensure features.html exists in the dev-store

- **If `~/.claude/feature-docs/<PROJECT>/features.html` exists**: use
  it.
- **Otherwise, if `features.md` exists at the repo root**: migrate.
  Use `~/.claude/skills/feature/features-template.html` as the basis.
  Set the `<title>`, `<h1>`, and subtitle for the project. Render the
  existing markdown tables into the template's sections: `In
  Progress` rows → `<section id="in-progress">` tbody; `Available` →
  `<section id="available">`; `Done` (if present) →
  `<section id="done">`; `Suggested order` (if present) → keep as
  prose/list in `<section id="suggested-order">`. Convert each
  `[text](path)` link to `<a href="path">text</a>`. Rewrite
  feature-doc hrefs from the legacy repo-relative form
  `docs/features/<feature>/<artifact>.md` to the dev-store-sibling
  form `<feature>/<artifact>.html` (e.g.
  `docs/features/rule-ir/context.md` →
  `rule-ir/context.html`), so the canonical tracker has working
  click-through. Leave hrefs that don't match this pattern alone.
  Drop any `<tr class="empty">` placeholders for tbodies that
  now have real rows. Write the file to
  `~/.claude/feature-docs/<PROJECT>/features.html`.
- **Otherwise, if neither exists**: skip this entire step. The
  project doesn't use a tracker.

### Move the feature into In Progress

Ask the user for their name if you don't know it.

If the feature already has an `Available` row, remove it and add an
equivalent `In Progress` row (with three cells: Feature, Owner,
Notes — Owner gets the user's name).

If the feature isn't in any tracker section yet (claimed cold, no
prior context capture), append a new `<tr>` to the `In Progress`
section's `<tbody>` with:

- `<td class="feature-name"><a href="<FEATURE>/context.html">FEATURE</a></td>`
- `<td class="feature-owner">…user's name…</td>`
- `<td class="feature-notes">…one-line note about scope or status…</td>`

If the `In Progress` tbody had a `<tr class="empty">` placeholder,
remove it now.

### Export to the repo (if configured) and commit

Check `.feature-workflow.toml`'s `[export].features` key. If
`markdown`:

```bash
feature-html-to-md \
    ~/.claude/feature-docs/<PROJECT>/features.html \
    features.md
```

If `html`:

```bash
cp ~/.claude/feature-docs/<PROJECT>/features.html features.html
```

If `none` or absent, skip the export and skip the commit — the claim
is local-only.

If something was exported, stage and commit only that file with the
message `Claim <FEATURE> in features.md`, then push — so others can
see it's being worked on.

## Step 3: Read context

Read the following:

- `CLAUDE.md` (architecture and conventions).
- Any spec or design doc the user has pointed to, including anything
  linked from `features.md` for this feature.
- The captured context for this feature, in this order of preference:
  1. `~/.claude/feature-docs/<PROJECT>/<FEATURE>/context.html` if it
     exists — the new canonical location.
  2. Otherwise `docs/features/<FEATURE>/context.md` if it exists — the
     legacy location, still valid for features captured before the
     HTML migration.

  Treat the context as historical background, not as a spec to
  transcribe. The requirements document should be written fresh,
  drawing on this context where relevant but not constrained by it.
- Any other design docs in the repo that look relevant to the feature.
  Don't restrict yourself to the repo root — explore anywhere that may
  help.

## Step 4: Draft

Use `~/.claude/skills/feature/requirements-template.html` as the basis.
Copy its CSS and JavaScript verbatim. Render the requirements into the
template's structure.

Write to `~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html`.
Create parent dirs with `mkdir -p` if needed.

Update in the template:

- `<title>`, the `<h1>` (feature name), the subtitle.
- The TOC entries to match the actual sections present (omit any TOC
  entry whose section you've dropped).
- The JS `docId` constant — e.g. `docs/features/<FEATURE>/requirements`.

### Sections

A good requirements doc contains:

- **Problem** (`id="problem"`): what's broken or missing, with concrete
  examples.
- **Vision** (`id="vision"`): one-sentence description of the solved
  state, wrapped in `<p class="vision-statement">`.
- **User stories** (`id="user-stories"`): rendered as
  `<ol class="stories">` with `<li>` cards. Each story carries
  `<div class="actor">As a [role]</div>`,
  `<div class="want">I want [capability]</div>`, and
  `<div class="scenario">Concrete situation</div>` — every story needs a
  concrete scenario, not just abstract desire.
- **Data model** (`id="data-model"`, if relevant): what's stored and
  how it relates to the existing schema; relationships, not exact column
  types.
- **Technical approach** (`id="technical-approach"`): high-level how, not
  implementation detail.
- **Alternatives considered** (`id="alternatives"`, optional): rendered
  as `<ol class="alternatives">`; each `<li>` has `.alt-title`,
  `.alt-source` (inline source citation — "discussed with user", "from
  design doc X"), and `.alt-reason`. Skip the section entirely if the
  user pre-chose the approach and no real alternatives came up — don't
  fabricate to fill space.
- **Delivery phases** (`id="delivery-phases"`): each phase as a
  `<div class="phase">` containing a `<div class="phase-header">` (badge
  + h3) and prose. Ordered increments that each deliver testable value;
  each phase becomes one MR.
- **Indicative implementation notes** (`id="indicative-notes"`,
  optional, at the bottom): plan-level detail worth carrying forward
  without polluting the requirements body — see "Requirements vs plan"
  below.
- **Design notes** (`id="design-notes"`, optional, populated during
  iteration): decisions and reasoning captured from review rounds.

Omit any optional section (and its TOC entry) if you have nothing real
to put in it. Don't pad.

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
implementation notes** at the bottom. The plan skill reads this section
to carry forward useful context.

### Tradeoff guidance

- Prefer simplicity over flexibility. Build for the current need.
- Prefer extending existing patterns over introducing new abstractions.
- Privacy and security are constraints, not afterthoughts. Flag anything
  that stores user data or crosses trust boundaries.
- You can propose deferring part of a feature — either as a later phase
  or as a new entry in the feature tracker. Not everything needs to be
  in scope.

### Export to the repo (if configured)

Check `.feature-workflow.toml` at the repo root. The relevant key is
`[export].requirements`. If the file is absent or the key is missing or
set to `"none"`, skip this step.

Otherwise:

- **`markdown`**:

  ```bash
  mkdir -p docs/features/<FEATURE>
  feature-html-to-md \
      ~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html \
      docs/features/<FEATURE>/requirements.md
  ```

- **`html`**:

  ```bash
  mkdir -p docs/features/<FEATURE>
  cp ~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html \
     docs/features/<FEATURE>/requirements.html
  ```

Remember the export-target path; you'll commit it at handoff (Step 8).

### Open it

```bash
google-chrome ~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html &
```

The trailing `&` backgrounds the browser process so the agent doesn't
wait.

## Step 5: Present and review in parallel

Tell the user the draft is ready for their review and that the HTML is
open in Chrome. Spawn a reviewer subagent using the Agent tool with
`run_in_background: true` so it runs while the human reads.

Prompt for the reviewer:

> You are reviewing a requirements document for a feature.
> Read the document at `~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html`.
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

The user may leave click-to-comment annotations inline in
`requirements.html` while reading. Those come back as a "Copy comments"
JSON blob in Step 6b.

## Step 6: Produce feedback synthesis document

For each piece of reviewer feedback, decide your take:

- **My take** should say whether you agree or disagree with reasoning
  — if agreeing, note how you'd address it; if disagreeing, explain
  why the requirement is correct as written.
- For feedback flagging plan-level detail in the requirements, the
  options are:
  1. **Accept and remove**: it's not load-bearing context.
  2. **Move to Indicative implementation notes**: useful for planning,
     but doesn't belong in the requirements body (see "Requirements vs
     plan" in Step 4).
  3. **Disagree**: it's genuinely a requirement constraint, not a plan
     choice.

### Triage

Items get bucketed into three tiers:

- **Needs your input**: product/conceptual decisions, scope or
  phasing trade-offs, deferral decisions, naming for concepts,
  anything you're not confident about, anything where you might be
  making assumptions about dev velocity.
- **Routine**: only items you're highly confident are
  uncontroversial — factual citation/path fixes, naming mechanics
  (rename X to Y), wording polish, defensive-test additions,
  observability/logging granularity, schema minor specs.
- **Feedback** (the middle): everything else, in the reviewer's
  original order.

When in doubt, prefer **Feedback** over **Routine**. The cost of a
Feedback item that turns out to be uncontroversial is small; the
cost of a misclassified Routine item is larger.

Item-level guidance:

- **Numbered titles**: descriptive enough that a reader grasps the
  issue at a glance. Number continuously across all three tiers
  (1, 2, 3, …), not restarting per section.
- **Detail paragraph**: include when the title alone isn't
  self-evident. Skip in the Routine tier.
- **My take**: focus on substance. Length matches the complexity of
  the call. In the Routine tier, keep it to one line.
- **"Your thoughts"**: left blank in the top and middle tiers (the
  HTML form provides the textareas). The Routine tier has no input
  — the user pushes back in chat if needed.

### Pick the next N

Count existing requirements-feedback files across both the dev-store
(`~/.claude/feature-docs/<PROJECT>/<FEATURE>/`, including
`.feedback-archive/`) and the legacy repo location
(`docs/features/<FEATURE>/`, including `.feedback-archive/`). Take
the max N and increment. If none exist, `N = 1`.

### Write the HTML synthesis doc

Use `~/.claude/skills/feature/feedback-template.html` as the basis.
Copy its CSS and JavaScript verbatim. Render the triaged items into
the template's three-tier structure.

Write to `~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements-feedback-<N>.html`.
Create parent dirs with `mkdir -p` if needed.

Update in the template:
- `<title>`, the `<h1>`, the subtitle.
- The meta line (item counts).
- The textarea total in the footer.
- The JS `docId` constant — e.g. `docs/features/<FEATURE>/requirements-feedback-<N>`.

### Open it

```bash
google-chrome ~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements-feedback-<N>.html &
```

### Hand off

Tell the user the synthesis doc is open. You'll wait for them to:

1. Click **Copy responses** in the synthesis doc and paste the JSON
   blob back, AND/OR
2. Leave click-to-comment annotations in `requirements.html` and click
   **Copy comments** to paste that JSON blob back.

They may paste one, the other, or both — and may iterate (paste
synthesis, then add comments later, etc.).

## Step 6b: Integrate feedback

Two JSON shapes can arrive in chat:

**Synthesis-doc responses** (from `requirements-feedback-<N>.html`):

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

**Click-to-comment annotations** (from `requirements.html`):

```json
{
  "doc": "docs/features/<FEATURE>/requirements",
  "comments": [
    {"excerpt": "...", "text": "user comment"}
  ]
}
```

Each comment is a piece of marginalia anchored to a selected passage.

### Sanity-check the `doc` field

Before integrating either blob, verify the `doc` field matches what
you expect for this feature and round:

- Synthesis blob: expected
  `docs/features/<FEATURE>/requirements-feedback-<N>` for the round
  you just opened in Step 6.
- Click-to-comment blob: expected
  `docs/features/<FEATURE>/requirements`.

If the value doesn't match (wrong feature, wrong round, or a stale
tab from another session), warn the user inline ("the pasted blob's
`doc` field is `X`, but I expected `Y` — looks like the wrong tab.
Confirm before I integrate?") and don't proceed until they
acknowledge. The blob author may legitimately want to apply
cross-session annotations, but the default assumption is mistaken
paste.

If the user signals completion without pasting anything (e.g. "i'm
done"), ask which they meant: the synthesis blob, the comments blob,
or both. Don't proceed without explicit input.

### Re-render requirements.html

After collecting and reasoning over the inputs, **rewrite
`requirements.html` from scratch** — a fresh render that incorporates:

- Synthesis responses (your decisions per item).
- Routine-flag items (the user's pushback).
- Click-to-comment annotations (each treated as an additional piece of
  feedback, integrated into the relevant section).

The fresh render mirrors the historical markdown workflow:
mid-iteration in-place edits aren't enough — we re-render so the
canonical HTML reflects the full integrated state.

Capture decisions that would otherwise be lost: check user annotations
for design principles, broader reasoning, or open questions beyond the
specific decision. Distill these into the **Design notes** section
(`id="design-notes"`) of `requirements.html` (add the section if it
doesn't exist). Keep entries to one or two lines, cite the source
review round. Ensure declined suggestions land in **Alternatives
considered** or as inline notes with the user's reasoning.

### Re-run the export (if configured)

If `.feature-workflow.toml` opts in for `requirements`, re-run the
export step (markdown or HTML copy) so the repo snapshot reflects the
integrated state.

### Archive the synthesis doc

```bash
PROJECT=$(basename $(git rev-parse --show-toplevel))
mkdir -p ~/.claude/feature-docs/$PROJECT/<FEATURE>/.feedback-archive
mv ~/.claude/feature-docs/$PROJECT/<FEATURE>/requirements-feedback-<N>.html \
   ~/.claude/feature-docs/$PROJECT/<FEATURE>/.feedback-archive/
```

The synthesis doc is transient; the integrated state lives in
`requirements.html` and the design-notes section. Tell the user the
rewrite is ready and that they can refresh the Chrome tab to see it.

Summarise the changes to the user.

## Step 7: Iterate

If the user comes back with more feedback — a new round of click-to-
comment annotations, fresh chat instructions, or a request to go round
the loop again:

1. Re-read `requirements.html` to pick up its current state.
2. Apply the new feedback by rewriting `requirements.html` (the same
   fresh-render discipline as Step 6b).
3. If the changes are substantial, re-spawn the reviewer subagent on
   the updated HTML and produce a new synthesis doc
   (`requirements-feedback-2.html`, etc.) following Step 6.
4. Re-run the export (if configured).

Repeat until the user signals approval conversationally ("looks good",
"approved", "let's plan").

## Step 8: Handoff

When the user signals approval — any of: "looks good", "approved",
"let's plan", "ready to plan", "move on", "time to plan", or similar:

1. Re-confirm: integrate any unprocessed click-to-comment or synthesis
   feedback (per Step 6b) before proceeding.
2. Commit only what ended up in the repo via the export step:
   - If `[export].requirements` is `markdown` or `html`, commit
     `docs/features/<FEATURE>/requirements.{md,html}`.
   - If `[export].requirements` is `none` or absent, there's nothing
     to commit — the canonical HTML in the dev-store is local-only
     working memory. Skip the commit step.
3. Use the message `docs(<FEATURE>): add requirements`. Push.
4. Automatically continue into the planning stage without waiting to
   be asked. **Do NOT use the Skill tool to invoke `/feature-plan`** —
   it sets `disable-model-invocation: true`, which blocks the Skill
   tool. Read `~/.claude/skills/feature-plan/SKILL.md` and execute its
   instructions inline in this conversation.
