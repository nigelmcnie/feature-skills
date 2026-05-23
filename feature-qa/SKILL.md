---
name: feature-qa
description: Run the project's quality control commands. Use before committing or after completing a phase.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
---

# Quality Control Workflow

The project's `CLAUDE.md` is the single source of truth for what constitutes
quality here. This skill does nothing more than run those commands and
stop on failure.

## Step 1: Discover the QA commands

Read `CLAUDE.md`. Find the commands that must run to verify quality —
typically under a heading like "Commands", "Quality", "QA", "Testing",
or similar, or called out explicitly with text like "always run these
before committing".

If `CLAUDE.md` does not exist, or the QA commands are not clearly
identifiable, **stop and tell the user**:

> I can't determine the QA commands from `CLAUDE.md`. Please tell me
> what to run, or add a Commands section to `CLAUDE.md` listing the
> commands I should run before committing.

Do not guess. Do not attempt to derive commands from `package.json`,
`Makefile`, or other build files unless `CLAUDE.md` points you there.

## Step 2: Run each command

Run every command from Step 1, in the order given. All must succeed.
If any command fails, stop, report the failure to the user, and fix
the underlying issue before re-running.

## Step 3: Report

Once all commands pass, tell the user QA passed and list which commands
were run. That's it.
