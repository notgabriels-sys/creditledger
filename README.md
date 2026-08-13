# Creditledger

Creditledger is an offline command-line tool for consolidating **declared** music-release credits and allocation arithmetic before you enter them into label pages, distributor forms, metadata systems, or collaborator review documents.

It is an organizational consistency check, not legal advice and not a rights-management system. It never decides what a role or category means, who agreed to anything, or whether a declaration is correct.

## What it does

- Loads one local TOML declaration of contributors, tracks, credits, and optional user-named allocation categories.
- Validates contributor/track references, duplicate IDs and duplicate rows after case normalization, and contiguous track numbering.
- Requires every **declared** allocation category for a track to total exactly `100` using exact decimal arithmetic.
- Keeps category labels user-defined. `Composition`, `Master`, and similar labels are examples, not built-in rights advice.
- Builds one readable credits record, canonical credit/allocation CSVs, and a JSON manifest with SHA-256 fingerprints.
- Keeps local plan paths out of JSON and generated artifacts; only declared data and the plan fingerprint are recorded.

## What it does not do

- Does not verify consent, attribution, contracts, rights, publishing, registrations, payment instructions, ownership, platform requirements, or public release state.
- Does not contact contributors, publishers, PROs, distributors, platforms, or any network service.
- Does not upload, submit, register, publish, pay, or alter a project/audio asset.
- Does not infer an allocation category or fill a missing value. A valid local plan is still only a declared record.

Every result begins with:

```text
DECLARED CREDITS AND ALLOCATIONS - CONSENT, ACCURACY, CONTRACTS, RIGHTS, REGISTRATION, PAYMENT, AND PUBLICATION STATUS UNVERIFIED
```

## Install

Requires Python 3.11 or newer.

```bash
python3 -m pip install .
```

For development:

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest
```

## Create a declaration

Start from [examples/creditledger-example.toml](examples/creditledger-example.toml). It contains fictional names and values only.

```toml
[release]
title = "Example Release"
primary_artist = "Example Artist"
requirements_basis = "Credits and allocation values assembled for collaborator review; verify every field independently before external use."

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
percentage = 100
```

`contributors`, `tracks`, and `credits` must contain at least one row. `allocations` is optional. If you declare one or more allocation rows for a given `track_id` and `category`, the rows in that group must total exactly `100`. A track without an allocation group is rendered explicitly as having no declared allocation group; Creditledger does not invent one.

IDs are case-insensitive references. A credit or allocation must name a contributor and track declared in the same file. Track numbers must be contiguous from `1` so generated records have a stable order.

## Check without writing files

`check` validates and prints a declared record. It writes nothing.

```bash
creditledger check ./credits.toml
creditledger check ./credits.toml --json
```

The JSON has no absolute plan path. It includes the exact plan SHA-256 so a reviewer can tell which declaration was checked.

## Build a review bundle

`build` writes only to a **new** output directory. It refuses to replace an existing directory.

```bash
creditledger build ./credits.toml \
  --output ./reviews/example-release-credits
```

It creates:

- `CREDITS.md` — readable declared release context, track credits, category groups, totals, and the verification boundary.
- `credits.csv` — one canonical row per declared track credit.
- `allocations.csv` — one canonical row per declared allocation entry with its declared category total.
- `manifest.json` — structured declared data, the plan SHA-256, and hashes of the other artifacts.

`--json` prints artifact names only, not the output or plan path:

```bash
creditledger build ./credits.toml \
  --output ./reviews/example-release-credits \
  --json
```

## Interpreting a green check

An exit code of `0` proves only that the local declaration is structurally consistent and every allocation category you supplied adds to `100`. It does **not** prove that every necessary category was supplied, that names/roles/percentages were agreed, or that any external system contains the same values.

An exit code of `1` means the declaration or requested output location is invalid; no new bundle is written.

Before any external use, have relevant contributors verify their fields through the appropriate process, confirm agreements/registrations/payments separately, and read back saved platform fields or public credits independently.

## Test

```bash
python3 -m pytest
```

## License

[MIT](LICENSE)
