"""Tests for portable declared-credit review artifacts."""

import csv
import hashlib
import importlib
import json

import pytest

from creditledger.service import assess


def test_credit_report_module_is_available():
    """The package exposes a report writer separate from assessment logic."""
    try:
        module = importlib.import_module("creditledger.report")
    except ModuleNotFoundError:
        module = None

    assert module is not None


def test_writes_fingerprinted_declared_credit_artifacts(tmp_path):
    """One valid assessment becomes readable and spreadsheet-ready local records."""
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
    assessment = assess(plan_path)
    report = importlib.import_module("creditledger.report")
    write_bundle = getattr(report, "write_bundle", None)

    assert callable(write_bundle)
    output = tmp_path / "credit-review"
    files = write_bundle(assessment=assessment, output_dir=output)
    assert files.report_path.name == "CREDITS.md"
    assert files.credits_path.name == "credits.csv"
    assert files.allocations_path.name == "allocations.csv"
    assert files.manifest_path.name == "manifest.json"

    rendered = files.report_path.read_text(encoding="utf-8")
    assert assessment.status in rendered
    assert "Opening Signal" in rendered
    assert "Artist A" in rendered
    assert "Composition" in rendered
    assert str(plan_path) not in rendered

    with files.credits_path.open(encoding="utf-8", newline="") as handle:
        credit_rows = list(csv.DictReader(handle))
    assert credit_rows == [
        {
            "track_number": "1",
            "track_id": "opening-signal",
            "track_title": "Opening Signal",
            "contributor_id": "artist-a",
            "contributor_name": "Artist A",
            "role": "Production",
        }
    ]

    with files.allocations_path.open(encoding="utf-8", newline="") as handle:
        allocation_rows = list(csv.DictReader(handle))
    assert [row["percentage"] for row in allocation_rows] == ["50", "50"]
    assert {row["category_total"] for row in allocation_rows} == {"100"}

    manifest = json.loads(files.manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == assessment.status
    assert manifest["plan_sha256"] == hashlib.sha256(plan_path.read_bytes()).hexdigest()
    assert manifest["artifacts"] == ["CREDITS.md", "credits.csv", "allocations.csv"]
    assert str(plan_path) not in json.dumps(manifest)


def test_refuses_to_replace_an_existing_credit_review_directory(tmp_path):
    """A build must not overwrite a prior declared-credit record."""
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
""".lstrip(),
        encoding="utf-8",
    )
    output = tmp_path / "existing-credit-review"
    output.mkdir()
    report = importlib.import_module("creditledger.report")

    with pytest.raises(ValueError, match="must not already exist"):
        report.write_bundle(assessment=assess(plan_path), output_dir=output)

    assert list(output.iterdir()) == []
