# Example: binding the handoff protocol to herdr / herd-new

This is a **worked example, not part of the skills.** It shows how one
environment binds the neutral handoff payloads (`agent-handoff`,
`phase-report`; see [`handoff-protocol.md`](handoff-protocol.md)) to a concrete
agent-spawning mechanism — here, the `herdr` agent fleet via its `herd-new`
launcher.

The skills never reference any of this. A real binding lives in the developer's
own environment configuration (e.g. a global `CLAUDE.md` that every session
loads), where it can name whatever spawn mechanism that developer actually runs.
With no binding present the payloads render to plain prose and the workflow is
fully manual — so the skills work unchanged for anyone without herdr. Treat the
below as a template to adapt to your own tooling.

---

When running the feature workflow under herdr, the agent acts as an
**orchestrator** and uses herd-new instead of telling the developer to switch
sessions by hand. All coupling lives in this binding; the skills stay neutral.

## Roles

- **Orchestrator** — the long-lived **Opus** session running requirements → plan →
  review → iterate → ship. Spawns the implementer, watches MRs, drives the flow.
- **Implementer** — one **Sonnet** session per feature, spawned for
  `/feature-implement`, kept alive across all phases (its loaded context and
  knowledge of plan deviations are why one session is right).

## Acting on `agent-handoff`

When a handoff says to spawn, the launch is the same action the developer triggers
by hand ("start a new agent on the plan for X") — use the optional
[`feature-agent`](feature-agent/SKILL.md) skill so the command/model/naming rules
stay identical across both entry points.

- `when: now`, target model **differs** from the current one → spawn with herd-new:
  `HERDNEW_MODEL=<model>`, `HERDNEW_PROMPT=<command>`, and put the orchestrator's
  own herdr agent name in the prompt so the new agent can report back. Announce the
  launch first (herd-new skill).
- `when: now`, target model **same** as the current one → continue inline; don't spawn.
- `when: after-merge:<ref>` → don't act yet. Watch `<ref>` (`gh pr view` /
  `glab mr view`); once merged, act as for `now` — inline if the target model
  matches the orchestrator (the implement→review and iterate→ship cases: it's
  already Opus, so it just resumes), or spawn if it differs.

## Acting on `phase-report` (from the implementer it spawned)

It arrives via `herdr agent send <orchestrator> …`. On receipt:

1. **Read `notes` first** and weigh it before anything else (the protocol requires it).
2. Wait for `mr` to merge; then run the `safe` `post_merge` checks on `main`, and
   surface the `human` checks + any `verify_flags` to the developer.
3. `status: phase-complete` → wake the idle implementer for the next phase:
   `herdr agent send <impl> "<wake>"` + Enter; confirm with `herdr agent read <impl>`.
4. `status: all-complete` → act on the attached `agent-handoff` to `/feature-review`
   — being Opus like the orchestrator, it resumes inline.

## If the agent is the spawned implementer (worker)

If the launch prompt named an orchestrator, the worker reports its `phase-report`
back to it via `herdr agent send <orchestrator> …` + Enter (not the human
fallback), then idles until woken. Before going quiet for good (after
`all-complete`), it drains the session: `/feature-retro` (persists to the webapp)
and any global/session retro the environment defines (transcript-only — lost
otherwise).

## Mechanics that carry the weight

- **Spawn** = `HERDNEW_PROMPT` + `HERDNEW_MODEL`, background by default.
- **Wake / report-back** = `herdr agent send` + Enter to an idle agent; always
  `herdr agent read` to confirm it landed.
- **Merge gate** = poll the MR with the platform CLI; the orchestrator stays the
  live driver across the wait.
- **One implementer per feature** — only its compaction limit should ever end it
  early, never the workflow.

## Fallback

None of this is in the skills. With no herdr present (or for another developer) the
payloads render to plain prose and the workflow is fully manual — unchanged.
