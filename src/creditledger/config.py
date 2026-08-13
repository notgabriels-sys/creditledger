"""Typed loading for declared credit and allocation records."""

import tomllib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


class PlanValidationError(ValueError):
    """A declared credit plan is incomplete or cannot be interpreted safely."""


@dataclass(frozen=True)
class Contributor:
    identifier: str
    name: str


@dataclass(frozen=True)
class Track:
    identifier: str
    number: int
    title: str


@dataclass(frozen=True)
class Credit:
    track_id: str
    contributor_id: str
    role: str


@dataclass(frozen=True)
class Allocation:
    track_id: str
    category: str
    contributor_id: str
    percentage: Decimal


@dataclass(frozen=True)
class CreditPlan:
    title: str
    primary_artist: str
    requirements_basis: str
    contributors: tuple[Contributor, ...]
    tracks: tuple[Track, ...]
    credits: tuple[Credit, ...]
    allocations: tuple[Allocation, ...]


def load_plan(path: Path) -> CreditPlan:
    """Load one UTF-8 TOML declaration into typed credit records."""
    return load_plan_bytes(path.read_bytes())


def load_plan_bytes(contents: bytes) -> CreditPlan:
    """Load exact plan bytes so a caller can retain their source fingerprint."""
    try:
        data = tomllib.loads(contents.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise PlanValidationError("plan must be UTF-8 encoded TOML") from error
    release = _section(data, "release")
    plan = CreditPlan(
        title=_non_empty_string(release, "title", "release.title"),
        primary_artist=_non_empty_string(
            release, "primary_artist", "release.primary_artist"
        ),
        requirements_basis=_non_empty_string(
            release, "requirements_basis", "release.requirements_basis"
        ),
        contributors=tuple(
            _contributor(item, index)
            for index, item in enumerate(_records(data, "contributors"))
        ),
        tracks=tuple(
            _track(item, index) for index, item in enumerate(_records(data, "tracks"))
        ),
        credits=tuple(
            _credit(item, index) for index, item in enumerate(_records(data, "credits"))
        ),
        allocations=tuple(
            _allocation(item, index)
            for index, item in enumerate(_optional_records(data, "allocations"))
        ),
    )
    _validate_unique_contributor_ids(plan.contributors)
    _validate_unique_track_ids(plan.tracks)
    _validate_track_numbers(plan.tracks)
    _validate_references(plan)
    _validate_unique_credit_entries(plan.credits)
    _validate_unique_allocation_entries(plan.allocations)
    _validate_allocation_totals(plan.allocations)
    return plan


def _contributor(item: Any, index: int) -> Contributor:
    name = f"contributors[{index}]"
    return Contributor(
        identifier=_non_empty_string(item, "id", f"{name}.id"),
        name=_non_empty_string(item, "name", f"{name}.name"),
    )


def _track(item: Any, index: int) -> Track:
    name = f"tracks[{index}]"
    return Track(
        identifier=_non_empty_string(item, "id", f"{name}.id"),
        number=_positive_integer(item, "number", f"{name}.number"),
        title=_non_empty_string(item, "title", f"{name}.title"),
    )


def _credit(item: Any, index: int) -> Credit:
    name = f"credits[{index}]"
    return Credit(
        track_id=_non_empty_string(item, "track_id", f"{name}.track_id"),
        contributor_id=_non_empty_string(
            item, "contributor_id", f"{name}.contributor_id"
        ),
        role=_non_empty_string(item, "role", f"{name}.role"),
    )


def _allocation(item: Any, index: int) -> Allocation:
    name = f"allocations[{index}]"
    return Allocation(
        track_id=_non_empty_string(item, "track_id", f"{name}.track_id"),
        category=_non_empty_string(item, "category", f"{name}.category"),
        contributor_id=_non_empty_string(
            item, "contributor_id", f"{name}.contributor_id"
        ),
        percentage=_percentage(item, "percentage", f"{name}.percentage"),
    )


def _records(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    records = _optional_records(data, key)
    if not records:
        raise PlanValidationError(f"{key} must contain at least one TOML table")
    return records


def _optional_records(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise PlanValidationError(f"{key} must be a list of TOML tables")
    return value


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise PlanValidationError(f"{key} must be a TOML table")
    return value


def _non_empty_string(section: Any, key: str, name: str) -> str:
    if not isinstance(section, dict) or key not in section:
        raise PlanValidationError(f"{name} is required")
    value = section[key]
    if not isinstance(value, str) or not value.strip():
        raise PlanValidationError(f"{name} must be a non-empty string")
    return value.strip()


def _positive_integer(section: Any, key: str, name: str) -> int:
    if not isinstance(section, dict) or key not in section:
        raise PlanValidationError(f"{name} is required")
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PlanValidationError(f"{name} must be a positive integer")
    return value


def _percentage(section: Any, key: str, name: str) -> Decimal:
    if not isinstance(section, dict) or key not in section:
        raise PlanValidationError(f"{name} is required")
    value = section[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PlanValidationError(
            f"{name} must be a number greater than zero and at most 100"
        )
    try:
        percentage = Decimal(str(value))
    except InvalidOperation as error:
        raise PlanValidationError(
            f"{name} must be a number greater than zero and at most 100"
        ) from error
    if not percentage.is_finite() or percentage <= 0 or percentage > 100:
        raise PlanValidationError(
            f"{name} must be a number greater than zero and at most 100"
        )
    return percentage


def _validate_allocation_totals(allocations: tuple[Allocation, ...]) -> None:
    totals: dict[tuple[str, str], Decimal] = {}
    for allocation in allocations:
        key = (allocation.track_id.casefold(), allocation.category.casefold())
        totals[key] = totals.get(key, Decimal()) + allocation.percentage
    for total in totals.values():
        if total != Decimal(100):
            raise PlanValidationError(
                "each declared allocation group must total exactly 100"
            )


def _validate_unique_allocation_entries(allocations: tuple[Allocation, ...]) -> None:
    seen: set[tuple[str, str, str]] = set()
    for allocation in allocations:
        key = (
            allocation.track_id.casefold(),
            allocation.category.casefold(),
            allocation.contributor_id.casefold(),
        )
        if key in seen:
            raise PlanValidationError(
                "duplicate allocation contributor entry in one declared allocation group"
            )
        seen.add(key)


def _validate_unique_credit_entries(credits: tuple[Credit, ...]) -> None:
    seen: set[tuple[str, str, str]] = set()
    for credit in credits:
        key = (
            credit.track_id.casefold(),
            credit.contributor_id.casefold(),
            credit.role.casefold(),
        )
        if key in seen:
            raise PlanValidationError("duplicate credit entry after case normalization")
        seen.add(key)


def _validate_references(plan: CreditPlan) -> None:
    contributor_ids = {
        contributor.identifier.casefold() for contributor in plan.contributors
    }
    track_ids = {track.identifier.casefold() for track in plan.tracks}
    for credit in plan.credits:
        _validate_reference(credit.track_id, track_ids, "track")
        _validate_reference(credit.contributor_id, contributor_ids, "contributor")
    for allocation in plan.allocations:
        _validate_reference(allocation.track_id, track_ids, "track")
        _validate_reference(allocation.contributor_id, contributor_ids, "contributor")


def _validate_track_numbers(tracks: tuple[Track, ...]) -> None:
    actual = sorted(track.number for track in tracks)
    expected = list(range(1, len(tracks) + 1))
    if actual != expected:
        raise PlanValidationError("track numbers must be contiguous from 1")


def _validate_unique_contributor_ids(contributors: tuple[Contributor, ...]) -> None:
    seen: set[str] = set()
    for contributor in contributors:
        normalized = contributor.identifier.casefold()
        if normalized in seen:
            raise PlanValidationError(
                "duplicate contributor id after case normalization"
            )
        seen.add(normalized)


def _validate_unique_track_ids(tracks: tuple[Track, ...]) -> None:
    seen: set[str] = set()
    for track in tracks:
        normalized = track.identifier.casefold()
        if normalized in seen:
            raise PlanValidationError("duplicate track id after case normalization")
        seen.add(normalized)


def _validate_reference(
    identifier: str, known_identifiers: set[str], kind: str
) -> None:
    if identifier.casefold() not in known_identifiers:
        raise PlanValidationError(f"{kind} reference names an undeclared {kind}")
