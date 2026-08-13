"""Portable declared-credit review artifacts."""

import csv
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .service import AllocationGroup, CreditAssessment, TrackAssessment


@dataclass(frozen=True)
class BundleFiles:
    report_path: Path
    credits_path: Path
    allocations_path: Path
    manifest_path: Path


def write_bundle(*, assessment: CreditAssessment, output_dir: Path) -> BundleFiles:
    """Write one new local review bundle from an already-valid declared assessment."""
    _validate_output_dir(output_dir)
    output_dir.mkdir()
    report_path = output_dir / "CREDITS.md"
    credits_path = output_dir / "credits.csv"
    allocations_path = output_dir / "allocations.csv"
    manifest_path = output_dir / "manifest.json"
    _write_report(assessment, report_path)
    _write_credits_csv(assessment, credits_path)
    _write_allocations_csv(assessment, allocations_path)
    _write_manifest(
        assessment, manifest_path, (report_path, credits_path, allocations_path)
    )
    return BundleFiles(
        report_path=report_path,
        credits_path=credits_path,
        allocations_path=allocations_path,
        manifest_path=manifest_path,
    )


def _validate_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        raise ValueError("output_dir must not already exist")
    if not output_dir.parent.is_dir():
        raise ValueError("output_dir parent must be an existing directory")


def _write_report(assessment: CreditAssessment, path: Path) -> None:
    plan = assessment.plan
    lines = [
        "# Declared credits record",
        "",
        "## Boundary",
        "",
        f"`{assessment.status}`",
        "",
        (
            "This is a local normalization of declared credit and allocation data. It does not "
            "confirm consent, accuracy, contracts, rights, registration, payment, publication, "
            "or any external platform field. An allocation total of 100 only confirms arithmetic "
            "within the values supplied to this tool."
        ),
        "",
        "## Declared release context",
        "",
        f"- Title: {plan.title}",
        f"- Primary artist: {plan.primary_artist}",
        f"- Requirements basis: {plan.requirements_basis}",
        f"- Plan SHA-256: `{assessment.plan_sha256}`",
        "",
        "## Tracks",
        "",
    ]
    for track in assessment.tracks:
        lines.extend(_track_markdown(track))
    lines.extend(
        [
            "## Before using these data externally",
            "",
            "- Have every relevant person verify the wording, role, and allocation values separately.",
            "- Confirm any agreements, registrations, payment instructions, and platform-specific requirements outside this tool.",
            "- Compare the final entered platform fields with the approved record and preserve independent evidence of the saved/public state.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _track_markdown(track: TrackAssessment) -> list[str]:
    lines = [
        f"### {track.number:02d}. {track.title}",
        "",
        f"- Track ID: `{track.identifier}`",
    ]
    lines.extend(["", "#### Declared credits", ""])
    if not track.credits:
        lines.extend(["No declared credit rows.", ""])
    else:
        lines.extend(
            [
                "| Contributor | Contributor ID | Role |",
                "| --- | --- | --- |",
            ]
        )
        for credit in track.credits:
            lines.append(
                "| "
                f"{_markdown_cell(credit.name)} | {_markdown_cell(credit.identifier)} | "
                f"{_markdown_cell(credit.role)} |"
            )
        lines.append("")
    lines.extend(["#### Declared allocation groups", ""])
    if not track.allocation_groups:
        lines.extend(["No declared allocation groups.", ""])
        return lines
    for group in track.allocation_groups:
        lines.extend(_allocation_group_markdown(group))
    return lines


def _allocation_group_markdown(group: AllocationGroup) -> list[str]:
    lines = [
        f"##### {group.category} (declared total: {_decimal_text(group.total)}%)",
        "",
        "| Contributor | Contributor ID | Declared percentage |",
        "| --- | --- | ---: |",
    ]
    for entry in group.entries:
        lines.append(
            "| "
            f"{_markdown_cell(entry.name)} | {_markdown_cell(entry.contributor_id)} | "
            f"{_decimal_text(entry.percentage)}% |"
        )
    lines.append("")
    return lines


def _write_credits_csv(assessment: CreditAssessment, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "track_number",
                "track_id",
                "track_title",
                "contributor_id",
                "contributor_name",
                "role",
            ],
        )
        writer.writeheader()
        for track in assessment.tracks:
            for credit in track.credits:
                writer.writerow(
                    {
                        "track_number": track.number,
                        "track_id": track.identifier,
                        "track_title": track.title,
                        "contributor_id": credit.identifier,
                        "contributor_name": credit.name,
                        "role": credit.role,
                    }
                )


def _write_allocations_csv(assessment: CreditAssessment, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "track_number",
                "track_id",
                "track_title",
                "category",
                "contributor_id",
                "contributor_name",
                "percentage",
                "category_total",
            ],
        )
        writer.writeheader()
        for track in assessment.tracks:
            for group in track.allocation_groups:
                for entry in group.entries:
                    writer.writerow(
                        {
                            "track_number": track.number,
                            "track_id": track.identifier,
                            "track_title": track.title,
                            "category": group.category,
                            "contributor_id": entry.contributor_id,
                            "contributor_name": entry.name,
                            "percentage": _decimal_text(entry.percentage),
                            "category_total": _decimal_text(group.total),
                        }
                    )


def _write_manifest(
    assessment: CreditAssessment, path: Path, artifacts: tuple[Path, Path, Path]
) -> None:
    payload = {
        "status": assessment.status,
        "release": {
            "title": assessment.plan.title,
            "primary_artist": assessment.plan.primary_artist,
            "requirements_basis": assessment.plan.requirements_basis,
        },
        "plan_sha256": assessment.plan_sha256,
        "tracks": [_manifest_track(track) for track in assessment.tracks],
        "artifacts": [artifact.name for artifact in artifacts],
        "artifact_sha256": {
            artifact.name: hashlib.sha256(artifact.read_bytes()).hexdigest()
            for artifact in artifacts
        },
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _manifest_track(track: TrackAssessment) -> dict[str, object]:
    return {
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


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
