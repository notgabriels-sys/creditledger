"""Tests for the declared credit-plan loader."""

import importlib
from decimal import Decimal

import pytest


def test_credit_plan_loader_module_is_available():
    """The package exposes a dedicated loader for one declared credit plan."""
    try:
        module = importlib.import_module("creditledger.config")
    except ModuleNotFoundError:
        module = None

    assert module is not None


def test_loads_a_declared_credit_plan_with_tracks_and_allocations(tmp_path):
    """One local TOML plan becomes typed, canonical declared records."""
    plan_path = tmp_path / "credits.toml"
    plan_path.write_text(
        """
[release]
title = "Example Release"
primary_artist = "Example Artist"
requirements_basis = "Credits and allocation values collected for collaborator review."

[[contributors]]
id = "artist-a"
name = "Artist A"

[[contributors]]
id = "artist-b"
name = "Artist B"

[[tracks]]
id = "opening-signal"
number = 1
title = "Opening Signal"

[[credits]]
track_id = "opening-signal"
contributor_id = "artist-a"
role = "Production"

[[allocations]]
track_id = "opening-signal"
category = "Composition"
contributor_id = "artist-a"
percentage = 50

[[allocations]]
track_id = "opening-signal"
category = "Composition"
contributor_id = "artist-b"
percentage = 50
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("creditledger.config")
    load_plan = getattr(config, "load_plan", None)
    load_plan_bytes = getattr(config, "load_plan_bytes", None)

    assert callable(load_plan)
    assert callable(load_plan_bytes)
    plan = load_plan(plan_path)
    assert plan.title == "Example Release"
    assert plan.primary_artist == "Example Artist"
    assert [(track.identifier, track.number) for track in plan.tracks] == [
        ("opening-signal", 1)
    ]
    assert [(credit.contributor_id, credit.role) for credit in plan.credits] == [
        ("artist-a", "Production")
    ]
    assert [allocation.percentage for allocation in plan.allocations] == [
        Decimal(50),
        Decimal(50),
    ]
    assert load_plan_bytes(plan_path.read_bytes()) == plan


def test_rejects_a_declared_allocation_group_that_does_not_total_100(tmp_path):
    """Declared percentages are only internally consistent when their group totals 100."""
    plan_path = tmp_path / "credits.toml"
    plan_path.write_text(
        """
[release]
title = "Example Release"
primary_artist = "Example Artist"
requirements_basis = "Credits and allocation values collected for collaborator review."

[[contributors]]
id = "artist-a"
name = "Artist A"

[[contributors]]
id = "artist-b"
name = "Artist B"

[[tracks]]
id = "opening-signal"
number = 1
title = "Opening Signal"

[[credits]]
track_id = "opening-signal"
contributor_id = "artist-a"
role = "Production"

[[allocations]]
track_id = "opening-signal"
category = "Composition"
contributor_id = "artist-a"
percentage = 40

[[allocations]]
track_id = "opening-signal"
category = "Composition"
contributor_id = "artist-b"
percentage = 50
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("creditledger.config")

    with pytest.raises(config.PlanValidationError, match="allocation group"):
        config.load_plan(plan_path)


def test_rejects_a_credit_that_names_an_undeclared_contributor(tmp_path):
    """Every credit row must resolve to a contributor declared in this plan."""
    plan_path = tmp_path / "credits.toml"
    plan_path.write_text(
        """
[release]
title = "Example Release"
primary_artist = "Example Artist"
requirements_basis = "Credits collected for collaborator review."

[[contributors]]
id = "artist-a"
name = "Artist A"

[[tracks]]
id = "opening-signal"
number = 1
title = "Opening Signal"

[[credits]]
track_id = "opening-signal"
contributor_id = "artist-b"
role = "Production"
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("creditledger.config")

    with pytest.raises(config.PlanValidationError, match="undeclared contributor"):
        config.load_plan(plan_path)


def test_rejects_noncontiguous_declared_track_numbers(tmp_path):
    """The printed credits order is unambiguous only with contiguous track numbers."""
    plan_path = tmp_path / "credits.toml"
    plan_path.write_text(
        """
[release]
title = "Example Release"
primary_artist = "Example Artist"
requirements_basis = "Credits collected for collaborator review."

[[contributors]]
id = "artist-a"
name = "Artist A"

[[tracks]]
id = "opening-signal"
number = 1
title = "Opening Signal"

[[tracks]]
id = "closing-signal"
number = 3
title = "Closing Signal"

[[credits]]
track_id = "opening-signal"
contributor_id = "artist-a"
role = "Production"
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("creditledger.config")

    with pytest.raises(config.PlanValidationError, match="contiguous"):
        config.load_plan(plan_path)


def test_rejects_duplicate_contributor_ids_after_case_normalization(tmp_path):
    """Contributor references need one stable ID even when display casing differs."""
    plan_path = tmp_path / "credits.toml"
    plan_path.write_text(
        """
[release]
title = "Example Release"
primary_artist = "Example Artist"
requirements_basis = "Credits collected for collaborator review."

[[contributors]]
id = "artist-a"
name = "Artist A"

[[contributors]]
id = "ARTIST-A"
name = "Artist A Duplicate"

[[tracks]]
id = "opening-signal"
number = 1
title = "Opening Signal"

[[credits]]
track_id = "opening-signal"
contributor_id = "artist-a"
role = "Production"
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("creditledger.config")

    with pytest.raises(config.PlanValidationError, match="duplicate contributor"):
        config.load_plan(plan_path)


def test_rejects_duplicate_track_ids_after_case_normalization(tmp_path):
    """Every credit target needs one stable track ID."""
    plan_path = tmp_path / "credits.toml"
    plan_path.write_text(
        """
[release]
title = "Example Release"
primary_artist = "Example Artist"
requirements_basis = "Credits collected for collaborator review."

[[contributors]]
id = "artist-a"
name = "Artist A"

[[tracks]]
id = "opening-signal"
number = 1
title = "Opening Signal"

[[tracks]]
id = "OPENING-SIGNAL"
number = 2
title = "Closing Signal"

[[credits]]
track_id = "opening-signal"
contributor_id = "artist-a"
role = "Production"
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("creditledger.config")

    with pytest.raises(config.PlanValidationError, match="duplicate track"):
        config.load_plan(plan_path)


def test_rejects_duplicate_contributor_entries_in_one_allocation_group(tmp_path):
    """A category cannot list the same contributor twice as separate declared shares."""
    plan_path = tmp_path / "credits.toml"
    plan_path.write_text(
        """
[release]
title = "Example Release"
primary_artist = "Example Artist"
requirements_basis = "Credits collected for collaborator review."

[[contributors]]
id = "artist-a"
name = "Artist A"

[[tracks]]
id = "opening-signal"
number = 1
title = "Opening Signal"

[[credits]]
track_id = "opening-signal"
contributor_id = "artist-a"
role = "Production"

[[allocations]]
track_id = "opening-signal"
category = "Composition"
contributor_id = "artist-a"
percentage = 50

[[allocations]]
track_id = "opening-signal"
category = "composition"
contributor_id = "ARTIST-A"
percentage = 50
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("creditledger.config")

    with pytest.raises(config.PlanValidationError, match="duplicate allocation"):
        config.load_plan(plan_path)


def test_rejects_duplicate_credit_entries_after_case_normalization(tmp_path):
    """The same declared role must not be repeated for one contributor and track."""
    plan_path = tmp_path / "credits.toml"
    plan_path.write_text(
        """
[release]
title = "Example Release"
primary_artist = "Example Artist"
requirements_basis = "Credits collected for collaborator review."

[[contributors]]
id = "artist-a"
name = "Artist A"

[[tracks]]
id = "opening-signal"
number = 1
title = "Opening Signal"

[[credits]]
track_id = "opening-signal"
contributor_id = "artist-a"
role = "Production"

[[credits]]
track_id = "OPENING-SIGNAL"
contributor_id = "ARTIST-A"
role = "production"
""".lstrip(),
        encoding="utf-8",
    )
    config = importlib.import_module("creditledger.config")

    with pytest.raises(config.PlanValidationError, match="duplicate credit"):
        config.load_plan(plan_path)
