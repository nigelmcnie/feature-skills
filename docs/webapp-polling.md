# Webapp polling convention

After writing a synthesis or feedback doc to the DB via the API, use the
webapp HTTP API to receive responses rather than waiting for a clipboard paste.

## Protocol (keyed API — current)

For docs authored via the logical-key API (`PUT /api/documents/...`):

1. **No force-walk needed** — docs authored via the API are immediately
   indexed in the DB. There is no need to POST to `/admin/discover`.

2. **Wait for submission** — use the bundled helper's `wait` verb (resolve
   `$WEBAPP` per `docs/webapp-helper.md`). It long-polls the endpoint and
   re-issues internally across the server's holds until the human submits or
   the deadline passes, so an arbitrarily long wait costs a **single**
   (backgroundable) invocation — not one agent turn per server hold. Run it in
   the background; you're notified when it returns.
   ```bash
   "$WEBAPP" wait \
     /api/documents/$PROJECT/$FEATURE/<doc_type>/$N/synthesis/wait --deadline 1800
   ```
   | Result | Action |
   |--------|--------|
   | helper exits non-zero (server unreachable) | Fall back to short poll (see below) |
   | `submitted=true` | Consume `responses` / `routine_flags` |
   | `submitted=false` | Deadline (`--deadline`, default 1800 s) elapsed with no submission — reconnect with another `wait`, or hand back: *"I'll pick up your feedback when you submit — ping me."* |

   `wait` absorbs the reconnect/backoff internally and bounds the total at
   `--deadline`, so there is **no hand-rolled reconnect schedule to run** — the
   helper is what turned the old "one turn per ~25 s hold" burn into one call.
   If the developer is plainly away, pass a shorter `--deadline` and hand back
   sooner rather than holding the full window.

3. **Short-poll fallback** — if `wait` errors (server unreachable), fall back
   to polling the read endpoint every 5 s:
   ```bash
   "$WEBAPP" get /api/documents/$PROJECT/$FEATURE/<doc_type>/$N/synthesis
   ```
   | Result | Action |
   |--------|--------|
   | helper exits non-zero (server unreachable) | Retry after 5 s |
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
   "$WEBAPP" post /admin/discover /dev/null >/dev/null 2>&1 || true
   ```

2. **Poll every 5 s**:
   ```bash
   "$WEBAPP" get "/synthesis-response?path=$HOME/.claude/feature-docs/<PROJECT>/<FEATURE>/<doc>.html"
   ```
   | Result | Action |
   |--------|--------|
   | helper exits non-zero (server unreachable) | Fall back to clipboard |
   | `404` | Not yet indexed — sleep 5, retry |
   | `200 submitted=false` | Awaiting the human — sleep 5, retry |
   | `200 submitted=true` | Consume `responses` / `routine_flags` |

New features use API-authored docs and the keyed protocol above.
