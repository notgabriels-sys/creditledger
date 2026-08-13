"""Canonical declared-credit assessments for review artifacts."""

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .config import Allocation, Contributor, Credit, CreditPlan, Track, load_plan_bytes

DECLARED_STATUS = (
    "DECLARED CREDITS AND ALLOCATIONS - CONSENT, ACCURACY, CONTRACTS, RIGHTS, "
    "REGISTRATION, PAYMENT, AND PUBLICATION STATUS UNVERIFIED"
)


@dataclass(frozen=True)
class CreditedContributor:
    identifier: str
    name: str
    role: str


@dataclass(frozen=True)
class AllocationEntry:
    contributor_id: str
    name: str
    percentage: Decimal


@dataclass(frozen=True)
class AllocationGroup:
    category: str
    entries: tuple[AllocationEntry, ...]
    total: Decimal


@dataclass(frozen=True)
class TrackAssessment:
    identifier: str
    number: int
    title: str
    credits: tuple[CreditedContributor, ...]
    allocation_groups: tuple[AllocationGroup, ...]


@dataclass(frozen=True)
class CreditAssessment:
    plan: CreditPlan
    plan_sha256: str
    status: str
    tracks: tuple[TrackAssessment, ...]


def assess(plan_path: Path) -> CreditAssessment:
    """Return a canonical local view of declared credits, without external verification."""
    plan_bytes = plan_path.read_bytes()
    plan = load_plan_bytes(plan_bytes)
    contributors = {
        contributor.identifier.casefold(): contributor
        for contributor in plan.contributors
    }
    tracks = tuple(
        _assess_track(track, plan.credits, plan.allocations, contributors)
        for track in sorted(plan.tracks, key=lambda item: item.number)
    )
    return CreditAssessment(
        plan=plan,
        plan_sha256=hashlib.sha256(plan_bytes).hexdigest(),
        status=DECLARED_STATUS,
        tracks=tracks,
    )


def _assess_track(
    track: Track,
    credits: tuple[Credit, ...],
    allocations: tuple[Allocation, ...],
    contributors: dict[str, Contributor],
) -> TrackAssessment:
    track_id = track.identifier.casefold()
    credited = tuple(
        sorted(
            (
                _credited_contributor(credit, contributors)
                for credit in credits
                if credit.track_id.casefold() == track_id
            ),
            key=lambda item: (
                item.role.casefold(),
                item.name.casefold(),
                item.identifier,
            ),
        )
    )
    allocation_groups = _allocation_groups(track_id, allocations, contributors)
    return TrackAssessment(
        identifier=track.identifier,
        number=track.number,
        title=track.title,
        credits=credited,
        allocation_groups=allocation_groups,
    )


def _credited_contributor(
    credit: Credit, contributors: dict[str, Contributor]
) -> CreditedContributor:
    contributor = contributors[credit.contributor_id.casefold()]
    return CreditedContributor(
        identifier=contributor.identifier,
        name=contributor.name,
        role=credit.role,
    )


def _allocation_groups(
    track_id: str,
    allocations: tuple[Allocation, ...],
    contributors: dict[str, Contributor],
) -> tuple[AllocationGroup, ...]:
    grouped: dict[str, tuple[str, list[AllocationEntry]]] = {}
    for allocation in allocations:
        if allocation.track_id.casefold() != track_id:
            continue
        category_key = allocation.category.casefold()
        _category, entries = grouped.setdefault(category_key, (allocation.category, []))
        contributor = contributors[allocation.contributor_id.casefold()]
        entries.append(
            AllocationEntry(
                contributor_id=contributor.identifier,
                name=contributor.name,
                percentage=allocation.percentage,
            )
        )
    return tuple(
        AllocationGroup(
            category=category,
            entries=tuple(
                sorted(
                    entries,
                    key=lambda item: (
                        item.name.casefold(),
                        item.name,
                        item.contributor_id,
                    ),
                )
            ),
            total=sum((entry.percentage for entry in entries), Decimal()),
        )
        for _, (category, entries) in sorted(grouped.items())
    )
