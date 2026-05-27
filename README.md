# feature-skills

[Claude Code](https://claude.com/claude-code) skills for a feature-development
workflow: requirements → plan → implement → review → iterate.

## The skills

| Skill | What it does |
|---|---|
| `feature` | Workflow router; detects state and delegates to the right sub-skill |
| `feature-context` | Capture an idea for later as a `context.md` |
| `feature-requirements` | Draft and review requirements |
| `feature-plan` | Draft and review an implementation plan |
| `feature-implement` | Implement one phase per MR |
| `feature-qa` | Run the project's quality control checks |
| `feature-review` | Review the merged implementation on `main` |
| `feature-iterate` | Address review feedback |

Most skills set `disable-model-invocation: true` and are invoked via slash
commands (`/feature-plan`, etc.). `feature-context` is the exception — it
can be auto-invoked when the user asks for a feature idea to be captured.

## Install

```bash
mkdir -p ~/src/nigelmcnie
cd ~/src/nigelmcnie
git clone git@github.com:nigelmcnie/feature-skills.git
cd feature-skills
./bin/install-symlinks
```

The install script symlinks each skill dir from this repo into
`~/.claude/skills/`, where Claude Code discovers them. Re-running the
script is safe.

## Typical flow

```
/feature                       # router, jumps to the right step
/feature-context <name>        # capture an idea for later
/feature-requirements <name>   # draft requirements
/feature-plan <name>           # plan it
/feature-implement <name>      # implement one phase (re-invoke per phase)
/feature-review <name>         # review after all phases merged
/feature-iterate <name>        # address review feedback
```

`/feature` picks up where you left off if you don't know the right
sub-skill to invoke.

## Design notes

- **Cross-skill conventions** live in `feature/feedback-template.md` and the
  doc templates at `feature/*-template.html`. Structural guidance for each
  artifact type (context, requirements, plan, features tracker) is carried
  in the HTML template comments; load-bearing principles
  (Requirements-vs-plan, Indicative notes convention, etc.) are inlined
  into each skill's `SKILL.md`.
- **Reviewer subagents** are spawned at requirements / plan / review / iterate.
  All skills here set `disable-model-invocation: true` so they can use the
  Agent tool (subagents can't spawn subagents).
- **Feedback synthesis docs** are archived locally to `.feedback-archive/`
  rather than deleted — locally gitignored.
- **Branch conventions**: requirements + plan commit to `main`. Implementation
  branches off `main` to `features/<feature>-p<N>`. Review runs on `main`
  after all phase MRs land.
