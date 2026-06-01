---
name: feature
description: Start or continue work on a feature. Checks current state and routes to the right stage of the feature workflow (requirements → plan → implement → review).
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
argument-hint: "[feature-name]"
---

# Feature Workflow Router

Route to the right stage of the feature workflow based on current state.

## Step 1: Establish the feature name

If `$ARGUMENTS` is provided, use it as the feature name (FEATURE).

If not, locate the project's feature tracker. The canonical tracker is
`~/.claude/feature-docs/<PROJECT>/features.html`, where `<PROJECT>` is
`basename $(git rev-parse --show-toplevel)`:

- **If `features.html` exists in the dev-store**: read its `In
  Progress` and `Available` sections, show them to the user, and ask
  which feature they want to work on.
- **Otherwise, if `features.md` exists at the repo root**: show its
  In Progress / Available sections to the user; they're still
  authoritative until a tracker-touching skill migrates the file to
  the dev-store on next write.
- **Otherwise**: ask the user what the feature is. Pick a short
  kebab-case name with them and confirm it. Call this FEATURE.

## Step 2: Offer workflow setup (first run)

If `~/.claude/feature-docs/<PROJECT>/.no-tracker` exists, the user
previously declined setup — skip this step entirely.

If **any** of `~/.claude/feature-docs/<PROJECT>/features.html`,
`features.md` at the repo root, or `.feature-workflow.toml` at the
repo root exists, setup has already happened (perhaps partially) —
skip this step.

Otherwise, offer once:

> This project doesn't have the feature workflow set up yet. Want me
> to scaffold it?
>
> 1. **features.html tracker** at
>    `~/.claude/feature-docs/<PROJECT>/features.html` — canonical,
>    local-only.
> 2. **`.feature-workflow.toml`** at the repo root with all four
>    `[export]` keys set to `"markdown"` — feature docs and the
>    tracker get exported to `docs/features/<feature>/` and
>    `features.md`, committed alongside code.
>
> Say no and we'll proceed without it (everything stays in the
> dev-store, nothing in the repo). To change the choice later,
> delete `~/.claude/feature-docs/<PROJECT>/.no-tracker`.

If accepted:

1. Create `~/.claude/feature-docs/<PROJECT>/features.html` from
   `~/.claude/skills/feature/features-template.html`. Set the
   `<title>`, `<h1>`, and subtitle for the project. Leave the
   tables empty (the template's `<tr class="empty">` placeholders
   are fine).
2. Write `.feature-workflow.toml` at the repo root with:

   ```toml
   [export]
   context = "markdown"
   requirements = "markdown"
   plan = "markdown"
   features = "markdown"
   ```
3. Run `feature-html-to-md
   ~/.claude/feature-docs/<PROJECT>/features.html features.md` to
   produce the initial repo snapshot, and commit `features.md` and
   `.feature-workflow.toml` together with the message
   `Add features tracker + workflow config`, then push.

If declined:

```bash
mkdir -p ~/.claude/feature-docs/$PROJECT
touch ~/.claude/feature-docs/$PROJECT/.no-tracker
```

Proceed without a tracker. Do not raise the offer again.

## Step 3: Detect state

Look at what exists for this feature. The canonical location is the
dev-store; the repo's `docs/features/<FEATURE>/` is an exported
snapshot (or absent if all `[export]` keys are `none`).

```bash
PROJECT=$(basename $(git rev-parse --show-toplevel))
ls ~/.claude/feature-docs/$PROJECT/$FEATURE/ 2>/dev/null
ls docs/features/$FEATURE/ 2>/dev/null
```

For the claim/owner: check the tracker. If
`~/.claude/feature-docs/<PROJECT>/features.html` exists, look at its
`In Progress` and `Done` sections for the feature's row and note the
Owner cell. Otherwise fall back to `features.md` at the repo root.

## Step 4: Route

Based on what exists, route to the appropriate sub-skill. Check the
dev-store first (canonical); fall back to the repo for legacy
features:

| State | Sub-skill |
|-------|-----------|
| Neither `requirements.html` (dev-store) nor `requirements.md` (repo) | `feature-requirements` |
| Has requirements, no `plan.html` (dev-store) or `plan.md` (repo) | `feature-plan` |
| Has plan with unchecked checklist items | `feature-implement` |
| All plan items checked, on a feature branch | `feature-review` |

To check for unchecked items:

- **HTML plan**: count `<li data-checklist-item="phase-…">` elements
  whose `<input>` lacks the `checked` attribute. A quick scan:

  ```bash
  grep -oE 'data-checklist-item="phase-[0-9]+-[0-9]+"[^>]*>[[:space:]]*<input[^>]*>' \
      ~/.claude/feature-docs/$PROJECT/$FEATURE/plan.html 2>/dev/null \
    | grep -vc ' checked' || echo 0
  ```

  The `[[:space:]]*` tolerates same-line whitespace between the `<li>`
  open tag and the `<input>`. The plan template's adjacency contract
  requires them on the same line — multi-line splits will make this
  detector miss items.

- **Markdown plan** (legacy):

  ```bash
  grep -c '\- \[ \]' docs/features/$FEATURE/plan.md 2>/dev/null || echo 0
  ```

**Do NOT use the Skill tool to invoke sub-skills.** All feature sub-skills have
`disable-model-invocation: true`, which blocks Skill tool invocation entirely.
This flag exists because several sub-skills spawn reviewer subagents via the
Agent tool — and subagents cannot themselves spawn subagents, so these skills
must always run in the main conversation context, never as a nested invocation.

Instead:
1. Tell the user which stage you're routing to and why.
2. Read the sub-skill's instructions from `/home/nigel/.claude/skills/<sub-skill>/SKILL.md`.
3. Execute those instructions inline in this conversation.
