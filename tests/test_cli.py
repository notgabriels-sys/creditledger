"""Tests for the declared-credit command-line interface."""

import hashlib
import importlib
import json


def test_credit_cli_module_is_available():
    """The package exposes a command-line entrypoint module."""
    try:
        module = importlib.import_module("creditledger.cli")
    except ModuleNotFoundError:
        module = None

    assert module is not None


def test_check_emits_a_path_free_declared_credit_record_without_writing(
    tmp_path, capsys
):
    """Checking a valid plan is read-only and keeps local plan paths out of JSON."""
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
category = "Master"
contributor_id = "artist-a"
percentage = 100
""".lstrip(),
        encoding="utf-8",
    )
    cli = importlib.import_module("creditledger.cli")
    main = getattr(cli, "main", None)

    assert callable(main)
    code = main(["check", str(plan_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["status"].startswith("DECLARED CREDITS AND ALLOCATIONS")
    assert payload["plan_sha256"] == hashlib.sha256(plan_path.read_bytes()).hexdigest()
    assert payload["tracks"][0]["credits"][0] == {
        "contributor_id": "artist-a",
        "contributor_name": "Artist A",
        "role": "Production",
    }
    assert payload["tracks"][0]["allocation_groups"] == [
        {
            "category": "Master",
            "total": "100",
            "entries": [
                {
                    "contributor_id": "artist-a",
                    "contributor_name": "Artist A",
                    "percentage": "100",
                }
            ],
        }
    ]
    assert str(plan_path) not in json.dumps(payload)


def test_build_writes_named_artifacts_and_reports_them_in_json(tmp_path, capsys):
    """Build writes only a separate new review directory and names its records."""
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
    output = tmp_path / "credit-review"
    cli = importlib.import_module("creditledger.cli")

    code = cli.main(["build", str(plan_path), "--output", str(output), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["artifacts"] == [
        "CREDITS.md",
        "credits.csv",
        "allocations.csv",
        "manifest.json",
    ]
    assert output.joinpath("CREDITS.md").is_file()
    assert output.joinpath("credits.csv").is_file()
    assert output.joinpath("allocations.csv").is_file()
    assert output.joinpath("manifest.json").is_file()
    assert str(output) not in json.dumps(payload)
