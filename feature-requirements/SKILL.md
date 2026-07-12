---
name: feature-requirements
description: Draft and review requirements for a feature. Writes the canonical requirements.html to the developer-scoped store and optionally exports markdown/HTML to the repo via .feature-workflow.toml. Use when starting work on a new feature, when the user describes something they want to build, or when there is no requirements doc yet for a feature they want to implement.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
argument-hint: "[feature-name]"
---

# Requirements Workflow

You are starting the requirements phase for a feature.

The requirements document and feedback synthesis docs are authored and
stored in the webapp's DB via the logical-key API. Documents are
addressed by `<PROJECT>/<FEATURE>/<doc_type>/<instance>`.
`<PROJECT>` is `basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"`
(worktree-safe — resolves to the main checkout's name even from inside a
phase worktree). The repo gets an exported snapshot, sourced from the DB, when
`.feature-workflow.toml` opts in.

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

First resolve PROJECT once and reuse it everywhere, plus the bundled `webapp`
helper (see `docs/webapp-helper.md`); `BASE` is this skill's base directory,
shown at the top of the invocation:

```bash
PROJECT=$(basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")")
WEBAPP="$(dirname "$(readlink -f "BASE")")/bin/webapp"
```

Now establish the feature. The **webapp is canonical** for whether a feature
already exists — `features.md` is only an exported snapshot and may lag, so a
feature can exist in the webapp (captured via the API) with no tracker row yet.
Do not use `features.md` alone to decide a feature is uncaptured.

- If `$ARGUMENTS` is provided, check the webapp first:

  ```bash
  "$WEBAPP" get /api/projects/$PROJECT/features/$ARGUMENTS 2>/dev/null
  ```

  A 200 means the feature already exists and was captured — use `$ARGUMENTS`
  as the feature name and read its context in Step 3, rather than eliciting a
  fresh description. Its `notes`, plus the Available section of `features.md`
  if present, give the description.
- Only if `$ARGUMENTS` is empty, or names a feature that exists in **neither**
  the webapp nor the `features.md` tracker, ask the user to describe what they
  want in a few sentences.

In either case, confirm the feature name with the user before proceeding.
Store this confirmed name — call it FEATURE — and use it for all file paths.
Do not use `$ARGUMENTS` directly in paths in case the user confirms a
different name.

Once FEATURE is confirmed, tell the user:

> → Run `/rename <FEATURE>` to name this session for the feature.

## Step 2: Claim the feature

Ask the user for their name if not already known — `claim` requires a
non-empty owner.

Call the claim API to move this feature from Available to In Progress:

```bash
printf '{"owner": "<user name>"}' \
  | "$WEBAPP" post /api/projects/$PROJECT/features/$FEATURE/claim -
```

A 200 response means the feature is now In Progress. If the webapp is
unreachable or the feature was never captured (404), skip silently —
the claim is best-effort.

## Step 3: Read context

Read the following:

- `CLAUDE.md` (architecture and conventions).
- Any spec or design doc the user has pointed to, including anything
  linked from `features.md` for this feature.
- The captured context for this feature, in this order of preference:
  1. `GET /api/documents/$PROJECT/$FEATURE/context/1` from the webapp
     — the canonical location when the context was authored via the API.
     Parse the `sections` array from the JSON response to read the
     content.
  2. `~/.claude/feature-docs/<PROJECT>/<FEATURE>/context.html` if it
     exists — legacy location for features captured before the API
     migration.
  3. `docs/features/<FEATURE>/context.md` if it exists — older legacy
     location.

  Treat the context as historical background, not as a spec to
  transcribe. The requirements document should be written fresh,
  drawing on this context where relevant but not constrained by it.
- Any other design docs in the repo that look relevant to the feature.
  Don't restrict yourself to the repo root — explore anywhere that may
  help.

## Step 4: Draft

**1. Fetch the manifest** to confirm the section keys for requirements:

```bash
"$WEBAPP" get /api/manifests/requirements
```

Use the returned section keys exactly. Also read `presentation.stylesheet_url` from the
response and follow `~/.claude/skills/feature/contract-grounding.md` to fetch the
presentation contract and ground all emitted HTML against it.

**2. Render the requirements** by assembling section HTML bodies, grounded against the
contract vocabulary.

**3. PUT the document**:

```bash
BODY=$(mktemp)
printf '%s' '{"sections": {"summary": "<p>…</p>", "vision": "…", …}, "actor": "agent"}' > "$BODY"
"$WEBAPP" put /api/documents/$PROJECT/$FEATURE/requirements/1 "$BODY"
```

The response includes `{"document_id": N, "url": "/doc/N", ...}`.
Note the `document_id` for later use in polling and comments endpoints.

**4. Run the lint gate** after the PUT succeeds:

```bash
doc-contract-lint --webapp http://127.0.0.1:8800 \
  $PROJECT/$FEATURE/requirements/1
```

A clean exit (0) means the doc is fully grounded. If violations are reported, fix the
class names in the section bodies, re-PUT, and re-run until the lint is clean.

Use `?dry_run=true` if you want to validate the section keys before committing:

```bash
"$WEBAPP" put "/api/documents/$PROJECT/$FEATURE/requirements/1?dry_run=true" "$BODY"
# → {"valid": true}
```

### Sections

A good requirements doc contains:

- **Summary** (`id="summary"`): the lead section — explain what we're
  implementing simply, in plain language with concrete examples, written
  for someone who hasn't read the rest of the doc. Cover what's broken or
  missing as part of this framing. No jargon. This is your answer to
  "explain what we're implementing simply, with examples".
- **Vision** (`id="vision"`): one-sentence description of the solved
  state. Use the contract's callout vocabulary for the visual treatment
  (see `doc.css` for the class).
- **User stories** (`id="user-stories"`): a list of story cards. Each
  card carries an actor role, a capability want, and a concrete scenario
  — every story needs a concrete scenario, not just abstract desire.
  Use the contract's story vocabulary (see `doc.css`).
- **Data model** (`id="data-model"`, if relevant): what's stored and
  how it relates to the existing schema; relationships, not exact column
  types.
- **Technical approach** (`id="technical-approach"`): high-level how, not
  implementation detail.
- **Alternatives considered** (`id="alternatives"`, optional): a list of
  alternatives with a title, a source citation, and a reason. Skip the
  section entirely if the user pre-chose the approach and no real
  alternatives came up — don't fabricate to fill space. Use the
  contract's alternatives vocabulary (see `doc.css`).
- **Delivery phases** (`id="delivery-phases"`): each phase uses the
  contract's phase vocabulary (badge + h3 header, followed by prose —
  see `doc.css` for the class names). Ordered increments that each
  deliver testable value; each phase becomes one MR.
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
- What's being built, what's broken or missing, and the desired outcome.
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
- **Bug-fix caveat**: when a fix is routed through the full feature
  workflow, the per-feature overhead (requirements → plan → review →
  ship) is already sunk — so when a minimal patch and a root-cause fix
  carry comparable risk, favour the root-cause fix. "Build for the
  current need" is a greenfield-scoping heuristic, not licence to patch a
  symptom when you're already opening the code. Surface the choice as a
  decision rather than defaulting to the smaller fix.
- Prefer extending existing patterns over introducing new abstractions.
- Privacy and security are constraints, not afterthoughts. Flag anything
  that stores user data or crosses trust boundaries.
- You can propose deferring part of a feature — either as a later phase
  or as a new entry in the feature tracker. Not everything needs to be
  in scope.

### Open it

The document is in the inbox at `http://127.0.0.1:8800` and viewable
at the `/doc/N` URL from the PUT response.

## Step 5: Present and review in parallel

Tell the user the draft is ready for their review and that the HTML is
in the inbox at `http://127.0.0.1:8800`. Spawn a reviewer subagent using the Agent tool with
`run_in_background: true` so it runs while the human reads.

Prompt for the reviewer:

> You are reviewing a requirements document for a feature.
> Fetch the document from the webapp API:
> `GET http://127.0.0.1:8800/api/documents/<PROJECT>/<FEATURE>/requirements/1`
> (use the JSON `sections` array; fall back to
> `~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html` on 404).
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
> - Deviations from the feature's context doc, `CLAUDE.md`, or any prior
>   recorded decision — call each out explicitly, with how far it diverges
> - Risk: which requirements are the hardest to reverse or have the widest
>   blast radius (stored user data, security, trust boundaries)?
>
> When any point you raise rests on how existing code behaves, read and cite
> that code rather than inferring it — and if the relevant code lives in
> another repo, say so and read it there (ask for the path if you don't have
> it) rather than asserting its behaviour. Mark any behaviour you could not
> verify as **unverified** instead of stating it as fact.
>
> Be specific. Reference sections by name. Focus on substance, not style.

The user may leave click-to-comment annotations inline in
`requirements.html` while reading. These are fetched via the webapp in
Step 6b when the synthesis is submitted.

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

**Before bucketing, verify any reviewer claim about how existing code
behaves.** When a finding's force depends on a factual premise about the
current code (especially code the reviewer flagged as unverified, or code in
another repo), check it against the source first. Do not escalate a decision
to **Needs your input** on an unverified premise — a wrong premise rubber-
stamped into requirements is expensive. If verifying is impractical, surface
the item as "verify X, then decide" rather than presenting the premise as
fact.

Items get bucketed into three tiers:

- **Needs your input**: product/conceptual decisions, scope or
  phasing trade-offs, deferral decisions, naming for concepts,
  anything you're not confident about, anything where you might be
  making assumptions about dev velocity. In particular, always surface:
  - anything your take resolves by **deferring, cutting, or not doing**
    something the reviewer raised — a confident "let's not" is still a
    direction decision; don't fold it down into Feedback as if agreed.
    For a defer/cut/scope item, the detail **must** carry the concrete
    **scenario(s)** the thing covers (a worked example, not an abstract
    description) so the developer can decide in one pass rather than
    asking you to "explain it simply" and round-tripping. And if your
    take **relies on a prior decision** ("we already decided X"),
    **verify that decision actually exists** — cite where — before
    leaning on it; an unsubstantiated "we decided" presented as settled
    is worse than saying it's open.
  - **high-risk** choices: hard to reverse, wide blast radius, or
    touching stored user data, security, or trust boundaries.
  - **deviations** from the context doc, `CLAUDE.md`, or a prior
    recorded decision — these capture what the developer already
    believes about the feature, so a meaningful divergence (not every
    wording difference) is where their input is most likely needed;
    name the divergence and its size.
- **Routine**: only items you're highly confident are
  uncontroversial — factual citation/path fixes, naming mechanics
  (rename X to Y), wording polish, defensive-test additions,
  observability/logging granularity, schema minor specs,
  **accuracy rewords** (correcting prose so it matches how the code or
  behaviour actually works), and **phasing-mechanics** corrections
  (resequencing or relabelling steps without changing scope). The last
  two land here, not in Feedback — **unless** the reword or resequencing
  would change a decision you'd want to weigh in on (a phasing
  *trade-off*, as opposed to a mechanics correction, stays **Needs your
  input**).
- **Feedback** (the middle): everything else, in the reviewer's
  original order.

When in doubt, prefer **Feedback** over **Routine**. The cost of a
Feedback item that turns out to be uncontroversial is small; the
cost of a misclassified Routine item is larger.

Item-level guidance:

- **Numbered titles**: descriptive enough that a reader grasps the
  issue at a glance. Number continuously across all three tiers
  (1, 2, 3, …), not restarting per section.
- **Detail paragraph**: explain the item simply, in plain language —
  what it is, where it occurs, and why it matters — so the reader
  grasps it without holding the full review in their head. Assume
  they haven't been following along closely: spell out jargon, name
  the concrete section, and avoid terse shorthand. A sentence or two
  is usually enough. Skip only in the Routine tier.
- **My take**: focus on substance. Length matches the complexity of
  the call. In the Routine tier, keep it to one line.
- **"Your thoughts"**: left blank in the top and middle tiers (the
  HTML form provides the textareas). The Routine tier has no input
  — the user pushes back in chat if needed.

### Pick the next N

Probe the API to find the first unused instance number — check from
N = 1 upward until you get a 404:

```bash
N=1
# The helper exits 0 on a 200 (doc exists) and non-zero on a 404 — so loop
# while it succeeds, stopping at the first unused instance.
while "$WEBAPP" get "/api/documents/$PROJECT/$FEATURE/requirements-feedback/$N" >/dev/null 2>&1; do
  N=$((N + 1))
done
```

This naturally covers archived instances (they remain in the DB).

### Write the feedback synthesis doc via the API

The feedback doc is an opaque HTML body. Build the full HTML document
using `~/.claude/skills/feature/feedback-template.html` as the basis
(copy its CSS and JavaScript verbatim; render the triaged items into
the three-tier structure; update `<title>`, `<h1>`, subtitle, meta
line, textarea total, and the JS `docId` constant to
`$PROJECT/$FEATURE/requirements-feedback/$N`).

Then PUT it to the API as an opaque body. Assemble
`{"body": "<full HTML document>", "actor": "agent"}` into a file — use a short
`json.dumps` helper so the HTML string is escaped correctly — then:

```bash
"$WEBAPP" put /api/documents/$PROJECT/$FEATURE/requirements-feedback/$N "$BODY"
```

The response includes `{"document_id": N_DOC, "url": "/doc/N_DOC", ...}`.
Call this `FEEDBACK_DOC_ID`.

### Open it

The feedback doc is in the inbox at `http://127.0.0.1:8800`.

### Wait for submission

Use the helper's `wait` verb — it long-polls and re-issues internally across
the server's holds until the human submits or the deadline passes, so an
arbitrarily long wait costs one backgroundable call, not one turn per hold
(see `docs/webapp-polling.md`). Run it in the background.

```bash
"$WEBAPP" wait \
  /api/documents/$PROJECT/$FEATURE/requirements-feedback/$N/synthesis/wait --deadline 1800
```

- helper exits non-zero → server unreachable; fall back to short poll (below).
- `submitted=true` → read `responses` and `routine_flags` from the JSON and
  proceed to Step 6b.
- `submitted=false` → the `--deadline` (default 1800 s) elapsed with no
  submission; reconnect with another `wait`, or hand back to the developer
  ("ping me when you submit"). `wait` bounds the total and handles the
  reconnect/backoff internally — there's no manual schedule to run.

**Short-poll fallback**: if `wait` errors (server unreachable), fall back to
polling `"$WEBAPP" get .../synthesis` every 5 seconds until `submitted=true`.

## Step 6b: Integrate feedback

Two inputs can arrive — via HTTP polling (Step 6) or as clipboard pastes if
the server was unavailable:

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

**Coverage check before trusting blanks.** A blank response means "shown
and agreed" — but a *missing* response key means "never rendered", which
must not be read as agreement (a webapp parse/render regression can drop
items the human never saw). The submission carries a key for every
decision-tier item the webapp rendered, even unanswered ones, and omits
items it didn't. So before integrating: confirm every top-tier and
middle-tier item number you authored appears as a key in `responses`. If
any are missing, the human never saw them — re-surface those specific
items (in chat, or by re-checking the synthesis doc renders them all)
and resolve them explicitly rather than silently treating them as agreed.

**Click-to-comment annotations** (from the requirements doc): fetch
from the webapp immediately after the synthesis response arrives, using
the document's logical key:

```bash
"$WEBAPP" get /api/documents/$PROJECT/$FEATURE/requirements/1/comments
```

If the `comments` array is non-empty, fold each comment in as additional
feedback — each is a piece of marginalia anchored to a selected passage.
After folding them in, mark the consumed ids as integrated so they don't
reappear next round:

```bash
printf '{"ids": [<ids from the GET response>]}' \
  | "$WEBAPP" post /api/documents/$PROJECT/$FEATURE/requirements/1/comments/integrate -
```

**Fallback**: if the server is unreachable, ask the user to click **Copy
comments** in the requirements doc and paste the JSON blob:

```json
{
  "doc": "<logical_key>",
  "comments": [{"excerpt": "...", "text": "user comment"}]
}
```

### Sanity-check (clipboard fallback only)

When using the clipboard fallback, verify the `doc` field of any pasted
blob — synthesis blob should have `doc` matching
`$PROJECT/$FEATURE/requirements-feedback/$N`, comments blob should match
`$PROJECT/$FEATURE/requirements/1`. If not, warn and confirm before
proceeding.

### Re-render requirements via the API

After collecting and reasoning over the inputs, **PUT fresh section
content** — a complete re-render of all sections that incorporates:

- Synthesis responses (your decisions per item).
- Routine-flag items (the user's pushback).
- Click-to-comment annotations (each treated as an additional piece of
  feedback, integrated into the relevant section).

The fresh PUT replaces all sections — mid-iteration in-place edits
aren't enough; we re-render so the canonical DB content reflects the
full integrated state.

Capture decisions that would otherwise be lost: distill them into the
**design-notes** section (add it if it doesn't exist). Keep entries to
one or two lines, cite the source review round. Ensure declined
suggestions land in **alternatives** or as inline notes.

```bash
BODY=$(mktemp)
printf '%s' '{"sections": {"summary": "…", "design-notes": "…", …}, "actor": "agent"}' > "$BODY"
"$WEBAPP" put /api/documents/$PROJECT/$FEATURE/requirements/1 "$BODY"
```

The feedback synthesis doc is transient (it served its purpose when
the synthesis was submitted). It remains in the DB but is now stale;
no archiving step is needed.

Tell the user the re-render is ready and that they can refresh the
inbox tab to see it.

Summarise the changes to the user.

## Step 7: Iterate

If the user comes back with more feedback — a new round of click-to-
comment annotations, fresh chat instructions, or a request to go round
the loop again:

1. GET the current requirements content from the API:
   ```bash
   "$WEBAPP" get /api/documents/$PROJECT/$FEATURE/requirements/1
   ```
2. Apply the new feedback and PUT the fresh sections (the same
   fresh-render discipline as Step 6b).
3. If the changes are substantial, re-spawn the reviewer subagent and
   produce a new feedback synthesis doc (using instance `N+1`) following
   Step 6.

Repeat until the user signals approval conversationally ("looks good",
"approved", "let's plan").

## Step 8: Handoff

When the user signals approval — any of: "looks good", "approved",
"let's plan", "ready to plan", "move on", "time to plan", or similar:

1. Re-confirm: integrate any unprocessed click-to-comment or synthesis
   feedback (per Step 6b) before proceeding.
2. Export and commit (if configured). Check `.feature-workflow.toml`
   at the repo root.

   **Export requirements** (if `[export].requirements = "markdown"`):

   ```bash
   mkdir -p docs/features/$FEATURE
   feature-html-to-md --webapp http://127.0.0.1:8800 \
       $PROJECT/$FEATURE/requirements/1 \
       docs/features/$FEATURE/requirements.md
   ```

   **Export features tracker** (if `[export].features = "markdown"`):

   ```bash
   feature-html-to-md --webapp http://127.0.0.1:8800 \
       --merge-features $PROJECT \
       features.md
   ```

   If either export ran, stage and commit only the exported files, then push.
   **Scope the commit with an explicit pathspec** (`git commit -- <paths>`):
   in a shared working tree a concurrent agent may have staged unrelated
   files, and a bare `git commit` would sweep them into your commit.

   ```bash
   git add docs/features/$FEATURE/requirements.md features.md  # as applicable
   git commit -m "docs: $FEATURE requirements" -- \
       docs/features/$FEATURE/requirements.md features.md  # as applicable
   git push
   ```

   If neither export ran, skip.
3. Automatically continue into the planning stage without waiting to
   be asked. **Do NOT use the Skill tool to invoke `/feature-plan`** —
   it sets `disable-model-invocation: true`, which blocks the Skill
   tool. Read `~/.claude/skills/feature-plan/SKILL.md` and execute its
   instructions inline in this conversation.
