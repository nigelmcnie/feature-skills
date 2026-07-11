"""Tests for _render_features_md (render-from-DB export) in feature-html-to-md."""

from __future__ import annotations

from pathlib import Path

# Load the script by exec — it has no .py extension so importlib.util won't work.
_SCRIPT = Path(__file__).parent.parent / "bin" / "feature-html-to-md"
_ns: dict = {}
exec(compile(_SCRIPT.read_text(), str(_SCRIPT), "exec"), _ns)  # noqa: S102

_render_features_md = _ns["_render_features_md"]


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _feat(slug: str, status: str, **kwargs) -> dict:
    return {"slug": slug, "status": status, "owner": None, "notes": None, **kwargs}


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------


class TestIdempotence:
    """Rendering the same DB state twice must produce byte-identical output."""

    def test_render_twice_identical(self):
        feats = [
            _feat("feat-a", "in_progress", owner="alice"),
            _feat("feat-b", "available"),
            _feat("feat-c", "parked"),
            _feat("feat-d", "done", notes="Shipped."),
        ]
        first = _render_features_md(feats, None)
        second = _render_features_md(feats, None)
        assert first == second

    def test_render_with_suggested_order_twice_identical(self):
        feats = [
            _feat("feat-b", "available"),
            _feat("feat-a", "available"),
        ]
        first = _render_features_md(feats, "feat-b\nfeat-a\n")
        second = _render_features_md(feats, "feat-b\nfeat-a\n")
        assert first == second

    def test_render_empty_features_identical(self):
        assert _render_features_md([], None) == _render_features_md([], None)


# ---------------------------------------------------------------------------
# DB-only notes appear in output
# ---------------------------------------------------------------------------


class TestDBOnlyNotes:
    """Notes stored only in the DB (no prior features.md) must appear in output."""

    def test_available_feature_notes_appear(self):
        feats = [_feat("feat-b", "available", notes="needs design review")]
        result = _render_features_md(feats, None)
        assert "needs design review" in result

    def test_in_progress_notes_appear(self):
        feats = [_feat("feat-a", "in_progress", owner="alice", notes="blocked on auth")]
        result = _render_features_md(feats, None)
        assert "blocked on auth" in result

    def test_parked_feature_notes_appear(self):
        feats = [_feat("feat-c", "parked", notes="waiting for product sign-off")]
        result = _render_features_md(feats, None)
        assert "waiting for product sign-off" in result

    def test_done_feature_notes_as_outcome(self):
        feats = [_feat("feat-d", "done", notes="Shipped via v3.2")]
        result = _render_features_md(feats, None)
        assert "Shipped via v3.2" in result

    def test_done_feature_no_notes_defaults_shipped(self):
        feats = [_feat("feat-d", "done")]
        result = _render_features_md(feats, None)
        assert "Shipped." in result


# ---------------------------------------------------------------------------
# suggested_order renders in its slot
# ---------------------------------------------------------------------------


class TestSuggestedOrder:
    """suggested_order text appears under a '## Suggested order' heading after Available."""

    def test_suggested_order_after_available_before_parked(self):
        feats = [
            _feat("feat-b", "available"),
            _feat("feat-c", "parked"),
        ]
        result = _render_features_md(feats, "feat-b\n")
        lines = result.splitlines()
        avail_idx = lines.index("## Available")
        parked_idx = lines.index("## Parked")
        order_lines = [
            i
            for i, line in enumerate(lines)
            if "feat-b" in line and avail_idx < i < parked_idx and not line.startswith("|")
        ]
        assert len(order_lines) > 0

    def test_suggested_order_after_available_before_done(self):
        feats = [
            _feat("feat-b", "available"),
            _feat("feat-d", "done"),
        ]
        result = _render_features_md(feats, "feat-b\n")
        lines = result.splitlines()
        avail_idx = lines.index("## Available")
        done_idx = lines.index("## Done")
        order_lines = [
            i
            for i, line in enumerate(lines)
            if "feat-b" in line and avail_idx < i < done_idx and not line.startswith("|")
        ]
        assert len(order_lines) > 0

    def test_suggested_order_heading_emitted(self):
        feats = [_feat("feat-b", "available")]
        result = _render_features_md(feats, "feat-b\nfeat-a\n")
        lines = result.splitlines()
        assert "## Suggested order" in lines
        heading_idx = lines.index("## Suggested order")
        # First non-empty line after the heading is the body text
        body_lines = [line for line in lines[heading_idx + 1 :] if line.strip()]
        assert body_lines[0] == "feat-b"

    def test_no_suggested_order_when_none(self):
        feats = [_feat("feat-b", "available")]
        result = _render_features_md(feats, None)
        # Output should just be the table with no extra prose or heading
        assert result.count("feat-b") == 1
        assert "## Suggested order" not in result

    def test_suggested_order_verbatim_multiline(self):
        feats = [_feat("feat-b", "available")]
        order_text = "feat-b\nfeat-a\n\nSome prose here.\n"
        result = _render_features_md(feats, order_text)
        assert "feat-b\nfeat-a\n\nSome prose here." in result

    def test_empty_available_still_places_suggested_order(self):
        """If Available has features and suggested_order is set, it always appears."""
        feats = [_feat("feat-x", "available"), _feat("feat-d", "done")]
        result = _render_features_md(feats, "feat-x\n")
        lines = result.splitlines()
        avail_idx = lines.index("## Available")
        done_idx = lines.index("## Done")
        # "feat-x" appears as table row AND in suggested_order text
        all_feat_x = [i for i, line in enumerate(lines) if "feat-x" in line]
        assert len(all_feat_x) >= 2
        # The non-table occurrence is between Available and Done
        non_table = [
            i for i in all_feat_x if avail_idx < i < done_idx and not lines[i].startswith("|")
        ]
        assert len(non_table) > 0


# ---------------------------------------------------------------------------
# Archived section
# ---------------------------------------------------------------------------


class TestArchivedSection:
    """archived features render in a dedicated '## Archived' section."""

    def test_full_metadata_reason_linked_superseded_by_and_note(self):
        feats = [
            _feat("feat-b", "available"),
            _feat(
                "feat-z",
                "archived",
                reason="duplicate",
                superseded_by="feat-b",
                note="see feat-b instead",
                archived_at="2024-06-01T00:00:00+00:00",
            ),
        ]
        result = _render_features_md(feats, None)
        assert "## Archived" in result
        assert "| Feature | Reason | Superseded by | Note |" in result
        assert "duplicate" in result
        assert "[feat-b](docs/features/feat-b/context.md)" in result
        assert "see feat-b instead" in result

    def test_non_resolving_superseded_by_rendered_as_text(self):
        feats = [
            _feat(
                "feat-z",
                "archived",
                reason="duplicate",
                superseded_by="no-such-feature",
                archived_at="2024-06-01T00:00:00+00:00",
            ),
        ]
        result = _render_features_md(feats, None)
        assert "no-such-feature" in result
        assert "[no-such-feature]" not in result

    def test_null_metadata_renders_empty_cells_without_crash(self):
        feats = [_feat("feat-z", "archived")]
        result = _render_features_md(feats, None)
        assert "## Archived" in result
        assert "feat-z" in result

    def test_archived_section_after_done_rows_newest_first(self):
        feats = [
            _feat("feat-d", "done"),
            _feat("feat-older", "archived", archived_at="2024-01-01T00:00:00+00:00"),
            _feat("feat-newer", "archived", archived_at="2024-06-01T00:00:00+00:00"),
        ]
        result = _render_features_md(feats, None)
        lines = result.splitlines()
        done_idx = lines.index("## Done")
        archived_idx = lines.index("## Archived")
        assert done_idx < archived_idx
        assert result.index("feat-newer") < result.index("feat-older")

    def test_no_archived_features_no_archived_heading(self):
        feats = [_feat("feat-b", "available")]
        result = _render_features_md(feats, None)
        assert "## Archived" not in result


# ---------------------------------------------------------------------------
# Fixed section order
# ---------------------------------------------------------------------------


class TestSectionOrder:
    """Sections appear in fixed order: In Progress / Available / Parked / Done."""

    def test_all_sections_fixed_order(self):
        feats = [
            _feat("feat-a", "in_progress", owner="alice"),
            _feat("feat-b", "available"),
            _feat("feat-c", "parked"),
            _feat("feat-d", "done"),
        ]
        result = _render_features_md(feats, None)
        lines = result.splitlines()
        ip_idx = lines.index("## In Progress")
        avail_idx = lines.index("## Available")
        parked_idx = lines.index("## Parked")
        done_idx = lines.index("## Done")
        assert ip_idx < avail_idx < parked_idx < done_idx

    def test_empty_sections_omitted(self):
        feats = [_feat("feat-b", "available")]
        result = _render_features_md(feats, None)
        assert "## In Progress" not in result
        assert "## Parked" not in result
        assert "## Done" not in result

    def test_in_progress_three_columns(self):
        feats = [_feat("feat-a", "in_progress", owner="bob", notes="on it")]
        result = _render_features_md(feats, None)
        assert "| Feature | Owner | Notes |" in result
        assert "bob" in result
        assert "on it" in result

    def test_available_two_columns(self):
        feats = [_feat("feat-b", "available")]
        result = _render_features_md(feats, None)
        assert "| Feature | Notes |" in result

    def test_done_outcome_column(self):
        feats = [_feat("feat-d", "done", notes="Shipped early")]
        result = _render_features_md(feats, None)
        assert "| Feature | Outcome |" in result
        assert "Shipped early" in result
