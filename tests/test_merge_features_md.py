"""Tests for _merge_features_md parked-feature support in feature-html-to-md."""

from __future__ import annotations

from pathlib import Path

# Load the script by exec — it has no .py extension so importlib.util won't work.
_SCRIPT = Path(__file__).parent.parent / "bin" / "feature-html-to-md"
_ns: dict = {}
exec(compile(_SCRIPT.read_text(), str(_SCRIPT), "exec"), _ns)  # noqa: S102

_merge_features_md = _ns["_merge_features_md"]


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_BASE_MD = """\
# My Features

## In Progress
| Feature | Owner | Notes |
|---|---|---|
| feat-a | alice | doing it |

## Available
| Feature | Notes |
|---|---|
| feat-b |  |

## Done
| Feature | Outcome |
|---|---|
| feat-old | Shipped. |
"""


def _feat(slug: str, status: str, **kwargs) -> dict:
    return {"slug": slug, "status": status, "owner": None, "notes": None, **kwargs}


# ---------------------------------------------------------------------------
# Parked block present in document
# ---------------------------------------------------------------------------


class TestParkedBlockPresent:
    """When ## Parked already exists in the document."""

    _MD_WITH_PARKED = """\
# My Features

## In Progress
| Feature | Owner | Notes |
|---|---|---|
| feat-a | alice | doing it |

## Available
| Feature | Notes |
|---|---|
| feat-b |  |

## Parked
| Feature | Notes |
|---|---|
| feat-c |  |

## Done
| Feature | Outcome |
|---|---|
| feat-old | Shipped. |
"""

    def test_parked_feature_stays_in_parked_section(self):
        db = {
            "feat-a": _feat("feat-a", "in_progress", owner="alice"),
            "feat-b": _feat("feat-b", "available"),
            "feat-c": _feat("feat-c", "parked"),
            "feat-old": _feat("feat-old", "done"),
        }
        result = _merge_features_md(self._MD_WITH_PARKED, db)
        lines = result.splitlines()
        parked_idx = lines.index("## Parked")
        # feat-c appears after ## Parked
        feat_c_idx = next(i for i, line in enumerate(lines) if "feat-c" in line)
        assert feat_c_idx > parked_idx

    def test_parked_feature_absent_from_available(self):
        db = {
            "feat-a": _feat("feat-a", "in_progress", owner="alice"),
            "feat-b": _feat("feat-b", "available"),
            "feat-c": _feat("feat-c", "parked"),
            "feat-old": _feat("feat-old", "done"),
        }
        result = _merge_features_md(self._MD_WITH_PARKED, db)
        lines = result.splitlines()
        avail_idx = lines.index("## Available")
        parked_idx = lines.index("## Parked")
        # feat-c must not appear between ## Available and ## Parked
        feat_c_occurrences = [i for i, line in enumerate(lines) if "feat-c" in line]
        assert all(i > parked_idx for i in feat_c_occurrences)
        assert avail_idx < parked_idx

    def test_feature_moved_from_available_to_parked(self):
        """A row previously in ## Available that the DB now marks parked moves to ## Parked."""
        db = {
            "feat-a": _feat("feat-a", "in_progress", owner="alice"),
            "feat-b": _feat("feat-b", "parked"),  # was available, now parked
            "feat-c": _feat("feat-c", "parked"),
            "feat-old": _feat("feat-old", "done"),
        }
        result = _merge_features_md(self._MD_WITH_PARKED, db)
        lines = result.splitlines()
        parked_idx = lines.index("## Parked")
        feat_b_lines = [i for i, line in enumerate(lines) if "feat-b" in line]
        assert all(i > parked_idx for i in feat_b_lines)
        # Should not appear under Available
        avail_idx = lines.index("## Available")
        assert all(i > parked_idx for i in feat_b_lines)
        # No feat-b between ## Available and ## Parked
        between = [i for i in feat_b_lines if avail_idx < i < parked_idx]
        assert between == []

    def test_feature_moved_from_parked_to_available(self):
        """A row previously in ## Parked that the DB now marks available moves to ## Available."""
        db = {
            "feat-a": _feat("feat-a", "in_progress", owner="alice"),
            "feat-b": _feat("feat-b", "available"),
            "feat-c": _feat("feat-c", "available"),  # was parked, now available
            "feat-old": _feat("feat-old", "done"),
        }
        result = _merge_features_md(self._MD_WITH_PARKED, db)
        lines = result.splitlines()
        avail_idx = lines.index("## Available")
        parked_idx = lines.index("## Parked")
        feat_c_lines = [i for i, line in enumerate(lines) if "feat-c" in line]
        # feat-c must appear in Available section (between ## Available and ## Parked)
        assert any(avail_idx < i < parked_idx for i in feat_c_lines)

    def test_no_duplicate_parked_section_synthesised(self):
        """When ## Parked already exists, no second ## Parked block is inserted."""
        db = {
            "feat-a": _feat("feat-a", "in_progress", owner="alice"),
            "feat-b": _feat("feat-b", "available"),
            "feat-c": _feat("feat-c", "parked"),
            "feat-old": _feat("feat-old", "done"),
        }
        result = _merge_features_md(self._MD_WITH_PARKED, db)
        assert result.count("## Parked") == 1


# ---------------------------------------------------------------------------
# Parked block absent — synthesis
# ---------------------------------------------------------------------------


class TestParkedBlockSynthesis:
    """When ## Parked is NOT in the document but parked features exist in DB."""

    def test_parked_section_synthesised_after_in_progress(self):
        db = {
            "feat-a": _feat("feat-a", "in_progress", owner="alice"),
            "feat-b": _feat("feat-b", "available"),
            "feat-new": _feat("feat-new", "parked"),
        }
        result = _merge_features_md(_BASE_MD, db)
        assert "## Parked" in result
        lines = result.splitlines()
        ip_idx = lines.index("## In Progress")
        parked_idx = lines.index("## Parked")
        avail_idx = lines.index("## Available")
        # ## Parked must appear between ## In Progress and ## Available
        assert ip_idx < parked_idx < avail_idx

    def test_new_parked_feature_emitted_with_notes_header(self):
        db = {
            "feat-a": _feat("feat-a", "in_progress", owner="alice"),
            "feat-new": _feat("feat-new", "parked", notes="blocked on X"),
        }
        result = _merge_features_md(_BASE_MD, db)
        assert "feat-new" in result
        assert "blocked on X" in result
        # Check it's under the Parked header
        lines = result.splitlines()
        parked_idx = lines.index("## Parked")
        feat_idx = next(i for i, line in enumerate(lines) if "feat-new" in line)
        assert feat_idx > parked_idx

    def test_parked_section_uses_two_column_table(self):
        db = {
            "feat-a": _feat("feat-a", "in_progress", owner="alice"),
            "feat-new": _feat("feat-new", "parked"),
        }
        result = _merge_features_md(_BASE_MD, db)
        lines = result.splitlines()
        parked_idx = lines.index("## Parked")
        # Next non-empty line after ## Parked should be the Feature | Notes header
        after = [line for line in lines[parked_idx + 1 :] if line.strip()]
        assert after[0] == "| Feature | Notes |"
        assert after[1] == "|---|---|"

    def test_synthesised_parked_section_separated_from_next_heading_by_blank_line(self):
        """The synthesised ## Parked block ends with a blank line before the next
        heading, matching every other section's spacing (else it runs straight into
        ## Available in the committed features.md)."""
        db = {
            "feat-a": _feat("feat-a", "in_progress", owner="alice"),
            "feat-b": _feat("feat-b", "available"),
            "feat-new": _feat("feat-new", "parked"),
        }
        result = _merge_features_md(_BASE_MD, db)
        assert "\n\n## Available" in result
        # And the last parked row is not glued to the next heading.
        assert "| feat-new |  |\n## Available" not in result

    def test_no_parked_section_synthesised_when_none_in_db(self):
        db = {
            "feat-a": _feat("feat-a", "in_progress", owner="alice"),
            "feat-b": _feat("feat-b", "available"),
        }
        result = _merge_features_md(_BASE_MD, db)
        assert "## Parked" not in result

    def test_parked_not_synthesised_when_parked_block_already_present(self):
        """Regression: parked block already in doc + parked in DB → no duplicate."""
        md = _BASE_MD + "\n## Parked\n| Feature | Notes |\n|---|---|\n| feat-x |  |\n"
        db = {
            "feat-a": _feat("feat-a", "in_progress", owner="alice"),
            "feat-b": _feat("feat-b", "available"),
            "feat-x": _feat("feat-x", "parked"),
        }
        result = _merge_features_md(md, db)
        assert result.count("## Parked") == 1

    def test_fallback_end_of_doc_when_no_in_progress_section(self):
        """When the doc has no ## In Progress, parked is appended at the end."""
        md = """\
# My Features

## Available
| Feature | Notes |
|---|---|
| feat-b |  |

## Done
| Feature | Outcome |
|---|---|
| feat-old | Shipped. |
"""
        db = {
            "feat-b": _feat("feat-b", "available"),
            "feat-new": _feat("feat-new", "parked"),
        }
        result = _merge_features_md(md, db)
        assert "## Parked" in result
        assert "feat-new" in result


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Merging a result back through merge should produce the same output."""

    def test_merge_is_idempotent_with_parked_block(self):
        db = {
            "feat-a": _feat("feat-a", "in_progress", owner="alice"),
            "feat-b": _feat("feat-b", "available"),
            "feat-c": _feat("feat-c", "parked"),
            "feat-old": _feat("feat-old", "done"),
        }
        md_with_parked = """\
# My Features

## In Progress
| Feature | Owner | Notes |
|---|---|---|
| feat-a | alice | doing it |

## Available
| Feature | Notes |
|---|---|
| feat-b |  |

## Parked
| Feature | Notes |
|---|---|
| feat-c |  |

## Done
| Feature | Outcome |
|---|---|
| feat-old | Shipped. |
"""
        first = _merge_features_md(md_with_parked, db)
        second = _merge_features_md(first, db)
        assert first == second

    def test_merge_is_idempotent_with_synthesised_parked(self):
        """After synthesis, re-merging over the result should be stable."""
        db = {
            "feat-a": _feat("feat-a", "in_progress", owner="alice"),
            "feat-b": _feat("feat-b", "available"),
            "feat-new": _feat("feat-new", "parked"),
        }
        first = _merge_features_md(_BASE_MD, db)
        second = _merge_features_md(first, db)
        assert first == second
