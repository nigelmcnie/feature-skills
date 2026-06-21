---
name: feature-plan
description: Create an implementation plan for a feature with approved requirements. Writes the canonical plan.html to the developer-scoped store and optionally exports markdown/HTML to the repo via .feature-workflow.toml. Use after requirements are approved, when the user says it's time to plan, or when there is a requirements doc but no plan yet for a feature they want to implement.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
argument-hint: "[feature-name]"
---

# Planning Workflow

You are creating an implementation plan for a feature whose requirements
have been approved.

The plan document is authored and stored in the webapp's DB via the
logical-key API, addressed as `<PROJECT>/<FEATURE>/plan/1`. `<PROJECT>`
is `basename $(git rev-parse --show-toplevel)`. The repo gets an
exported snapshot, sourced from the DB, when `.feature-workflow.toml`
opts in.

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

Resolve `PROJECT` once and reuse it:

```bash
PROJECT=$(basename $(git rev-parse --show-toplevel))
```

`$ARGUMENTS` is the feature name (`<FEATURE>`).

Read the following:

- The approved requirements for this feature, in this order of
  preference:
  1. `GET /api/documents/$PROJECT/$FEATURE/requirements/1` from the
     webapp — canonical when requirements were authored via the API.
     Parse the `sections` array from the JSON response. Include any
     **indicative-notes** section, which carries forward plan-level
     context that didn't belong in the requirements body.
  2. `~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html` if
     it exists — legacy location for features written before the API
     migration.
  3. `docs/features/<FEATURE>/requirements.md` — older legacy location.
- `CLAUDE.md` (architecture and conventions).
- All source modules referenced in the requirements' technical
  approach.
- Existing test files to understand testing patterns.

## Step 2: Draft

**1. Fetch the manifest** to confirm the section keys for a plan:

```bash
curl -fsS http://127.0.0.1:8800/api/manifests/plan
```

The plan manifest includes base sections (overview, key-decisions,
data-model, contract, file-structure, verification, qc, checklist)
plus a `repeated_prefixes: ["phase-"]` — each delivery phase is a
`phase-N` section key.

**2. Render the plan** by assembling section HTML bodies following the
structure described below.

**3. PUT the document**:

```bash
curl -fsS -X PUT \
  "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1" \
  -H 'Content-Type: application/json' \
  -d '{
    "sections": {
      "overview": "<p>…</p>",
      "key-decisions": "…",
      "phase-1": "…",
      "phase-2": "…",
      "checklist": "…"
    },
    "actor": "agent"
  }'
```

The response includes `{"document_id": N, "url": "/doc/N", ...}`.
Note the `document_id` — you will need it for comments endpoints.

Use `?dry_run=true` to validate section keys before committing:

```bash
curl -fsS -X PUT \
  "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1?dry_run=true" \
  -H 'Content-Type: application/json' \
  -d '{"sections": {…}}'
# → {"valid": true}
```

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
- **Verification**: machine-runnable acceptance commands (exact,
  copy-pasteable) that prove the feature works — the implementing agent
  runs them, and `feature-review` Step 6 re-runs them against main.
  **Confirm each command actually runs what you intend before writing it
  in** — e.g. that the named target is the full suite, not a fast subset
  (a project may have a `make check` that runs only a handful of tests
  while `make test` is the real suite). Prefer commands that fail loudly
  when the feature is absent over prose like "run the tests".
  If a verification step requires live credentials, interactive auth, or
  an external service, note it inline: `(Note: requires live credentials
  — perform manually if agent cannot obtain them)`.
- **Checklist**: a flat checklist of all steps across all phases at
  the bottom of the document. The implementing agent checks items off
  as it works.

### Detail level

The plan should be detailed enough that an implementing agent (which
may be a different, less capable model) can follow it without making
significant design decisions. Include:

- Function signatures with type hints.
- Schema changes.
- Key conditional logic ("if X, then Y; otherwise Z").
- Test descriptions (what's tested, not full test code).
- For items that parse a known HTML or data structure: a short representative sample (2–5 lines) or a pointer to an example file in the repo. An implementing agent on a cold start can't infer the structure from context alone.

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

Every checklist `<li>` **must** carry a stable
`data-checklist-item="phase-<N>-<step>"` attribute. `<N>` is the phase
number; `<step>` is the 1-indexed position of the item within that
phase. Example:

```html
<section id="checklist">
  <h2>Checklist</h2>
  <h3>Phase 1: Foo</h3>
  <ul class="checklist">
    <li data-checklist-item="phase-1-1"><input type="checkbox"><span class="label">Step A.</span></li>
    <li data-checklist-item="phase-1-2"><input type="checkbox"><span class="label">Step B.</span></li>
  </ul>
  <h3>Phase 2: Bar</h3>
  <ul class="checklist">
    <li data-checklist-item="phase-2-1"><input type="checkbox"><span class="label">Step C.</span></li>
  </ul>
</section>
```

`feature-implement` marks items checked by `data-checklist-item` ID
rather than positional or text matching, so the IDs must be unique
and stable across re-renders. If the plan iterates and items get
reordered or inserted, mint new IDs for new items but preserve
existing IDs for items that already exist.

**Adjacency contract**: keep `<li>` and the inner `<input>` on the
same line (or with only whitespace between them). The detector used
by `feature-implement` / the router greps for unchecked items via
the `<li ...><input...>` pattern; pretty-printing the checklist
across multiple lines would make the detector miss items and report
"all done" prematurely. Re-renders (Step 4 / Step 5 below) must
preserve the single-line item shape.

Items within each phase are ordered as they will be implemented.

### Quality control

Reference `CLAUDE.md` for quality control steps rather than hardcoding
them. Instruct the implementing agent to follow whatever `CLAUDE.md`
says at implementation time.

### Open it

The plan is in the inbox at `http://127.0.0.1:8800` and viewable at
the `/doc/N` URL from the PUT response.

## Step 3: Present and review in parallel

Tell the user the plan is ready for their review and that the HTML is
in the inbox at `http://127.0.0.1:8800`. Spawn a reviewer subagent using the Agent tool with
`run_in_background: true` so it runs while the human reads.

Prompt for the reviewer:

> You are reviewing an implementation plan for a feature.
> Fetch the plan from the webapp API:
> `GET http://127.0.0.1:8800/api/documents/<PROJECT>/<FEATURE>/plan/1`
> (use the JSON `sections` array; fall back to
> `~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html` on 404).
> Fetch the requirements similarly:
> `GET http://127.0.0.1:8800/api/documents/<PROJECT>/<FEATURE>/requirements/1`
> (fall back to `~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html`,
> then `docs/features/<FEATURE>/requirements.md`).
> Read `CLAUDE.md` for architectural context.
>
> Check:
> - Does the plan cover all requirements? Flag any gaps.
> - Are the file paths correct? Do the modules exist?
> - Does it account for cross-cutting concerns called out in `CLAUDE.md`?
> - Are there dependency issues or blockers?
> - Is the phasing sensible? Can each phase be independently tested?
> - Are the code snippets consistent with existing patterns?
> - Deviations: where does the plan diverge from the requirements, the
>   context doc, `CLAUDE.md`, or a prior decision? Call each out with its
>   magnitude.
> - Risk: which parts of the plan are the hardest to reverse or highest
>   blast radius (migrations, stored data, trust boundaries)?
>
> Be specific. Reference sections by name.

## Step 4: Process reviewer feedback inline

When the reviewer returns, triage each item into one of:

- **Apply** — you agree with the reviewer, and the change is
  uncontroversial: factual corrections, missed dependencies,
  citation/path fixes, polish, wording. This also covers **purely
  technical calls that have a clear low-risk default and no
  product/scope/strategic content** (e.g. which stdlib parser, how to
  scope a test guard, a threat-model boundary already implied by the
  requirements) — apply these directly with your resolution noted in
  the "Will apply" list, rather than asking. If you catch yourself
  labelling an item "low-stakes", it's an Apply, not an Ask.
- **Ask** — the item involves a real decision: product semantics,
  naming for concepts, scope or phasing trade-offs, deferral
  decisions, anything strategic, anything hard to reverse or high blast
  radius — in short, a choice the developer would plausibly answer
  differently from you. Surface inline with your take. Two easy-to-miss
  cases belong here: (1) anything your take resolves by **deferring,
  cutting, or not doing** something the reviewer raised — a confident
  "let's not" is still a direction decision, not an Apply; (2)
  **deviations** from the requirements, context doc, `CLAUDE.md`, or a
  prior recorded decision — these capture what the developer already
  believes, so a meaningful divergence is where their input is most
  likely needed.
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
> 1. <Question>. <Plain-language explanation: what this is about, why
>    it's a decision, and what's at stake — a sentence or two.> My
>    take: <brief>.
> 2. <Question>. <Explanation.> My take: <brief>.
>
> Reply with answers (or "go" to take my take on all of them) and I'll apply.

For each "Need your call" item, explain it simply before giving your
take — what it is, why it's a real decision, and what each direction
implies — assuming the user hasn't been following the review closely.
Spell out jargon and name the concrete section. Don't make the user
reverse-engineer the question from a terse one-liner.

When the user replies (with answers or "go"), also fetch active comments
from the webapp before applying anything, using the plan's logical key:

```bash
curl -fsS "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1/comments"
```

If the `comments` array is non-empty, fold each comment into the same
triage as reviewer feedback. After applying, integrate the consumed ids:

```bash
curl -fsS -X POST \
  "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1/comments/integrate" \
  -H 'Content-Type: application/json' \
  -d '{"ids": [<ids from GET>]}'
```

**Fallback**: if the server is unreachable, ask the user to click **Copy
comments** in the plan doc and paste the JSON blob:
`{"doc": "$PROJECT/$FEATURE/plan/1", "comments": [...]}`.

Wait for the user's response. Apply the "Will apply" items plus the
resolved questions and any actionable comment annotations.

If any "Need your call" answers reveal substantive design decisions
(principles, reasoning, broader implications beyond the specific item),
capture them in the **design-notes** section of the requirements doc.
GET the current requirements content, add/update the design-notes
section, then PUT the updated sections back:

```bash
curl -fsS "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/requirements/1"
# … update design-notes section …
curl -fsS -X PUT \
  "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/requirements/1" \
  -H 'Content-Type: application/json' \
  -d '{"sections": {…, "design-notes": "…"}, "actor": "agent"}'
```

### Re-render the plan via the API

After integrating the round of feedback, **PUT fresh section content**
— a complete re-render of all sections that incorporates all applied
items. Preserve existing `data-checklist-item` IDs for unchanged steps;
mint new IDs for new ones. The fresh-PUT discipline mirrors the
historical re-render workflow: the canonical DB content reflects the
full integrated state, not a patchwork.

```bash
curl -fsS -X PUT \
  "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1" \
  -H 'Content-Type: application/json' \
  -d '{"sections": {"overview": "…", "checklist": "…", …}, "actor": "agent"}'
```

Summarise what was applied to the user. They can refresh the inbox
tab to see the new render.

## Step 5: Iterate

If the user provides further feedback via chat instructions or if there
are new comments in the webapp, then at each iterate round fetch active
comments from the webapp first:

```bash
curl -fsS "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1/comments"
```

If the `comments` array is non-empty, fold them in and integrate the ids
(same as Step 4). Then:

1. GET the current plan content from the API:
   ```bash
   curl -fsS "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1"
   ```
2. Apply the new feedback and PUT the fresh sections (fresh-render discipline).
3. If the changes are substantial, re-spawn the reviewer subagent on the
   updated plan.
5. Follow Step 4 (triage) for any new reviewer feedback.

Repeat until the user approves conversationally.

## Step 6: Handoff

When the user signals approval — any of: "looks good", "approved",
"let's implement", "ready to implement", "start building", "time to
implement", or similar:

1. Re-confirm: fetch and integrate any remaining active comments from
   the webapp (same keyed `GET` + `POST .../comments/integrate` as
   Step 4) before proceeding.
2. Export and commit (if configured). Check `.feature-workflow.toml`
   at the repo root.

   **Export plan** (if `[export].plan = "markdown"`):

   ```bash
   mkdir -p docs/features/$FEATURE
   feature-html-to-md --webapp http://127.0.0.1:8800 \
       $PROJECT/$FEATURE/plan/1 \
       docs/features/$FEATURE/plan.md
   ```

   If the export ran, stage and commit the file, then push:

   ```bash
   git add docs/features/$FEATURE/plan.md
   git commit -m "docs: $FEATURE plan"
   git push
   ```

   If `[export].plan` is absent or `"none"`, skip.
3. Tell the user:

   > Plan approved. When you're ready to implement, switch to your Sonnet session and run:
   >
   > `/feature-implement <FEATURE>`

Do not invoke `/feature-implement` yourself.
