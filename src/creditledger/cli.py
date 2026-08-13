"""Command-line interface for declared-credit records."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .report import BundleFiles, write_bundle
from .service import CreditAssessment, assess


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="creditledger",
        description="Validate declared release credits and allocation arithmetic locally.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    for command in ("check", "build"):
        subparser = subcommands.add_parser(command)
        subparser.add_argument(
            "plan", type=Path, help="Path to a Creditledger TOML plan"
        )
        subparser.add_argument(
            "--json",
            action="store_true",
            help="Print a path-free machine-readable declared record",
        )
        if command == "build":
            subparser.add_argument(
                "--output",
                type=Path,
                required=True,
                help="New local directory for declared-credit review artifacts",
            )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Check or build declared-credit artifacts without external operations."""
    args = build_parser().parse_args(argv)
    try:
        assessment = assess(args.plan)
        files: BundleFiles | None = None
        if args.command == "build":
            files = write_bundle(assessment=assessment, output_dir=args.output)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    if args.json:
        payload = _as_json(assessment)
        if files is not None:
            payload["artifacts"] = [
                files.report_path.name,
                files.credits_path.name,
                files.allocations_path.name,
                files.manifest_path.name,
            ]
        print(json.dumps(payload, sort_keys=True))
    else:
        if files is not None:
            print(f"Built {files.report_path}")
            print(f"Built {files.credits_path}")
            print(f"Built {files.allocations_path}")
            print(f"Built {files.manifest_path}")
        _print_summary(assessment)
    return 0


def _print_summary(assessment: CreditAssessment) -> None:
    print(assessment.status)
    print(
        f"Declared release: {assessment.plan.primary_artist} - {assessment.plan.title}"
    )
    for track in assessment.tracks:
        print(
            f"{track.number:02d}. {track.title}: credits={len(track.credits)} "
            f"allocation_groups={len(track.allocation_groups)}"
        )
    print(
        "No consent, accuracy, contracts, rights, registration, payment, or publication "
        "state is verified."
    )


def _as_json(assessment: CreditAssessment) -> dict[str, object]:
    return {
        "status": assessment.status,
        "plan_sha256": assessment.plan_sha256,
        "release": {
            "title": assessment.plan.title,
            "primary_artist": assessment.plan.primary_artist,
            "requirements_basis": assessment.plan.requirements_basis,
        },
        "tracks": [
            {
                "id": track.identifier,
                "number": track.number,
                "title": track.title,
                "credits": [
                    {
                        "contributor_id": credit.identifier,
                        "contributor_name": credit.name,
                        "role": credit.role,
                    }
                    for credit in track.credits
                ],
                "allocation_groups": [
                    {
                        "category": group.category,
                        "total": _decimal_text(group.total),
                        "entries": [
                            {
                                "contributor_id": entry.contributor_id,
                                "contributor_name": entry.name,
                                "percentage": _decimal_text(entry.percentage),
                            }
                            for entry in group.entries
                        ],
                    }
                    for group in track.allocation_groups
                ],
            }
            for track in assessment.tracks
        ],
        "unverified": [
            "consent, accuracy, contracts, and rights are not verified",
            "registration, payment, platform fields, and publication are not verified",
            "no external person, service, or platform was contacted",
        ],
    }


def _decimal_text(value: object) -> str:
    rendered = format(value, "f")
    if "." not in rendered:
        return rendered
    return rendered.rstrip("0").rstrip(".") or "0"


if __name__ == "__main__":
    raise SystemExit(main())
