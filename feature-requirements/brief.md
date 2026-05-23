# Requirements Brief

## Purpose
You are drafting a requirements document for a feature. This brief guides
the structure and quality of that document.

## Structure
A good requirements document contains:
- **Problem**: what's broken or missing, with concrete examples
- **Vision**: one-sentence description of the solved state
- **User stories**: who benefits and how
- **Data model** (if relevant): what's stored and how it relates to existing schema
- **Technical approach**: high-level how, not implementation detail
- **Alternatives considered** (optional): approaches that were discussed but not chosen, with the reason. Skip the section if the user pre-chose the approach and no real alternatives came up — don't fabricate alternatives to fill space.
- **Delivery phases**: ordered increments that each deliver testable value
- **Indicative implementation notes** (optional, at the bottom): plan-level detail worth carrying forward without embedding in the requirements body. See "Requirements vs plan" below.

## Requirements vs plan

Requirements answer **what** and **why**. Plans answer **how**.

Belongs in requirements:
- Problem and desired outcome
- User-visible behaviour and constraints
- Data model relationships (that something is stored, not the schema)
- Architectural shape at "we'll do X, not Y" level
- Why specific tradeoffs were made

Belongs in the plan:
- Function signatures, schemas, exact APIs
- File paths and module structure
- Order of operations, phases, test coverage
- Code-level patterns and snippets

When in doubt, keep requirements abstract. If a piece of plan-level detail
feels too important to lose, put it in an **Indicative implementation notes**
section at the bottom of `requirements.md`. The plan skill reads this section
to carry forward useful context without polluting the requirements body.

## Tradeoff guidance
- Prefer simplicity over flexibility. Build for the current need.
- Prefer extending existing patterns over introducing new abstractions.
- Privacy and security are constraints, not afterthoughts. Flag anything
  that stores user data or crosses trust boundaries.
- You can propose deferring part of a feature — either as a later phase
  or as a new entry in the feature tracker. Not everything needs to be in scope.

## What to read
Before drafting, read:
- `CLAUDE.md` — architecture, conventions, and project-specific concerns
- `features.md` if the project has one — what exists, what's in progress
- Any design or context docs in the repo that inform the feature

## Quality checks
Before presenting the draft:
- Every user story has a concrete scenario, not just abstract desire
- Delivery phases are ordered so each is independently testable
- If the Alternatives section is present, every alternative is grounded — either discussed with the user, established by a design doc, or an obvious known pattern in the codebase. Inline the source (e.g. "discussed with user", "from design doc X"). Don't invent alternatives to fill the section.
- No implementation details in user stories (save for technical approach)
