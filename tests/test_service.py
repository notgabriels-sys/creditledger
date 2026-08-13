"""Tests for canonical declared-credit assessments."""

import hashlib
import importlib
from decimal import Decimal


def test_credit_assessment_module_is_available():
    """The package exposes an assessment layer separate from TOML parsing."""
    try:
        module = importlib.import_module("creditledger.service")
    except ModuleNotFoundError:
        module = None

    assert module is not None


def test_assessment_orders_declared_tracks_and_resolves_contributor_names(tmp_path):
    """Artifacts receive a stable, human-readable view of declared records."""
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
id = "closing-signal"
number = 2
title = "Closing Signal"

[[tracks]]
id = "opening-signal"
number = 1
title = "Opening Signal"

[[credits]]
track_id = "opening-signal"
contributor_id = "artist-b"
role = "Writing"

[[credits]]
track_id = "opening-signal"
contributor_id = "artist-a"
role = "Production"

[[allocations]]
track_id = "opening-signal"
category = "Composition"
contributor_id = "artist-b"
percentage = 50

[[allocations]]
track_id = "opening-signal"
category = "Composition"
contributor_id = "artist-a"
percentage = 50
""".lstrip(),
        encoding="utf-8",
    )
    service = importlib.import_module("creditledger.service")
    assess = getattr(service, "assess", None)

    assert callable(assess)
    assessment = assess(plan_path)
    assert assessment.plan_sha256 == hashlib.sha256(plan_path.read_bytes()).hexdigest()
    assert [track.number for track in assessment.tracks] == [1, 2]
    opening = assessment.tracks[0]
    assert [(credit.name, credit.role) for credit in opening.credits] == [
        ("Artist A", "Production"),
        ("Artist B", "Writing"),
    ]
    assert opening.allocation_groups[0].category == "Composition"
    assert opening.allocation_groups[0].total == Decimal(100)
    assert [entry.name for entry in opening.allocation_groups[0].entries] == [
        "Artist A",
        "Artist B",
    ]
