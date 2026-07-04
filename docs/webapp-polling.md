# Webapp polling convention

After writing a synthesis or feedback doc to the DB via the API, use the
webapp HTTP API to receive responses rather than waiting for a clipboard paste.

## Protocol (keyed API — current)

For docs authored via the logical-key API (`PUT /api/documents/...`):

1. **No force-walk needed** — docs authored via the API are immediately
   indexed in the DB. There is no need to POST to `/admin/discover`.

2. **Wait for submission** — issue a single held-connection call that
   returns as soon as the human submits (or after a bounded timeout):
   ```bash
   curl -fsS \
     "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/<doc_type>/$N/synthesis/wait"
   ```
   | Result | Action |
   |--------|--------|
   | `curl` error (server unreachable) | Fall back to short poll (see below) |
   | `404` | Doc not found — check the PUT succeeded |
   | `200 submitted=true` | Consume `responses` / `routine_flags` |
   | `200 submitted=false` | Timeout elapsed — re-issue per the reconnect schedule below |

   On a clean `submitted=false` timeout, follow this **deterministic
   reconnect schedule** — silently, with no status message — rather than
   reconnecting forever. The endpoint holds for up to ~240 s (about four
   minutes) before returning, so each reconnect lands cache-warm.

   1. **Active phase (first ~3 empty holds, ~12 min).** On a clean
      `submitted=false` timeout, re-issue the wait call immediately. This
      keeps coverage tight and cache-warm while the developer is most
      likely reviewing.
   2. **Backoff phase (after ~3 empty holds).** Stop tight reconnecting —
      you are past the cache window, so amortise with longer sleeps.
      Use `ScheduleWakeup` at widening delays (e.g. 15 min, then 30 min)
      and re-issue the wait call on each wake.
   3. **Hard stop (~30–45 min total with no submission).** Stop waiting
      and hand back to the developer with a one-line message such as
      *"I'll pick up your feedback when you submit — ping me."* A concrete
      bound is the point: it removes the wide variance in how long agents
      hold.

   **Why this shape.** Reconnecting every ~25 s (the old hold length)
   spends a full agent turn each time, so an unbounded loop burns tokens
   with no deterministic stop — some agents gave up in a minute, others
   held 15+ minutes. A ~240 s hold plus this schedule keeps the active
   phase cheap (each reconnect is cache-warm), amortises the tail with
   `ScheduleWakeup`, and bounds total waiting to a known ceiling.

   No time-of-day gating is applied — the schedule is purely elapsed-time
   based.

3. **Short-poll fallback** — if the wait call errors or the server is
   unreachable, fall back to polling every 5 s using the existing read
   endpoint:
   ```bash
   curl -fsS \
     "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/<doc_type>/$N/synthesis"
   ```
   | Result | Action |
   |--------|--------|
   | `curl` error (server unreachable) | Retry after 5 s |
   | `404` | Doc not found — check that the PUT succeeded |
   | `200 submitted=false` | Awaiting the human — sleep 5, retry |
   | `200 submitted=true` | Consume `responses` / `routine_flags` |

## Legacy path-based polling (dev-store docs)

For docs written to the dev-store by older skills, the path-based endpoint
is still available. The path **must be fully absolute and tilde-expanded** —
the walker stores `source_path` expanded, so a literal `~` never matches
and 404s forever. Use `$HOME`, which expands inside the quoted URL:

1. **Force-walk** — trigger the walker so the doc is indexed immediately:
   ```bash
   curl -fsS -X POST http://127.0.0.1:8800/admin/discover >/dev/null 2>&1 || true
   ```

2. **Poll every 5 s**:
   ```bash
   curl -fsS "http://127.0.0.1:8800/synthesis-response?path=$HOME/.claude/feature-docs/<PROJECT>/<FEATURE>/<doc>.html"
   ```
   | Result | Action |
   |--------|--------|
   | `curl` error (server unreachable) | Fall back to clipboard |
   | `404` | Not yet indexed — sleep 5, retry |
   | `200 submitted=false` | Awaiting the human — sleep 5, retry |
   | `200 submitted=true` | Consume `responses` / `routine_flags` |

New features use API-authored docs and the keyed protocol above.
