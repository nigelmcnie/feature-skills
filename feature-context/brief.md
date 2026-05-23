# Context Brief

## Purpose
Capture background for a feature that may be worked on later. This is the
historical ledger a future requirements session will draw on. It informs
requirements, but is not requirements itself.

## Structure
A good `context.md` contains:
- **Problem space and motivation**: why this might be worth doing, what's
  broken or missing, what conversations or observations triggered it
- **Related work**: existing patterns or features in the codebase that
  connect to this, including links to other `context.md` / `requirements.md`
  files when relevant
- **Constraints and considerations**: what to watch for, dependencies,
  prior decisions that shape the space
- **Links**: design docs, customer reports, Slack threads, tickets,
  external references
- **Open questions**: things worth resolving when requirements get written

## What it is not
- User stories (those belong in requirements)
- A technical approach or design (that belongs in requirements or the plan)
- A phase breakdown
- A spec to be transcribed verbatim into requirements
- A wishlist of features in disguise — keep it tightly scoped to one feature

## Guidance
- Distill, don't transcribe. The conversation may have been long; the
  `context.md` should be short enough to read in a couple of minutes.
- Capture *why* this came up, not just *what* was discussed.
- Use concrete examples where they sharpen the picture — code paths,
  filenames, error messages.
- Acknowledge what you don't know. A clear "open question" is more useful
  than a half-formed guess.
