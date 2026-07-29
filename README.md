# inaturalist-interact

Typed, tested utilities for retrieving and publishing Digital Botanical Gardens
Initiative (DBGI) data through iNaturalist.

The repository is being rebuilt incrementally. The first new workflow retrieves a
complete metadata snapshot for any iNaturalist project and derives the links between
observations and DBGI sample IDs stored in observation tags.

## Setup

Install dependencies with uv:

```bash
uv sync --dev
```

Run tests:

```bash
uv run pytest -q
```

## Retrieve a project metadataset

The default command retrieves every observation in the
[Digital Botanical Gardens Initiative project](https://www.inaturalist.org/projects/digital-botanical-gardens-initiative):

```bash
uv run inaturalist-interact fetch-project
```

By default, files are written to:

```text
data/exports/digital-botanical-gardens-initiative/
```

Choose another output directory or project by passing a project ID, slug, or URL:

```bash
uv run inaturalist-interact fetch-project \
  https://www.inaturalist.org/projects/digital-botanical-gardens-initiative \
  --output /path/to/snapshot
```

Retrieval uses the public iNaturalist API and does not require an access token.
Set `INATURALIST_ACCESS_TOKEN` when the snapshot should include metadata that is
visible to the authenticated account but not to the public.
The client requests the maximum supported page size, follows every page explicitly,
validates response shapes and counts, and preserves the complete nested response for
each observation.

### Snapshot files

Each snapshot contains:

- `project.json`: complete project metadata.
- `observations.jsonl`: the lossless metadataset, with one complete iNaturalist API
  observation per line.
- `observations.csv`: all top-level API fields. Nested fields such as photos,
  identifications, taxon data, comments, observation fields, and tags are JSON-encoded
  in their cells.
- `sample_id_links.csv`: one row per observation/DBGI sample association, including
  the exact source tag.
- `manifest.json`: retrieval timestamp, project identity, record counts, unique
  sample counts, duplicate-association counts, format version, and filenames.

Sample IDs are extracted case-insensitively from tags containing an exact
`dbgi_XXXXXX` identifier. For example, both `dbgi_001353` and
`emi_external_id:DBGI_001353` map to the canonical sample ID `dbgi_001353`.
Observations without a DBGI sample tag remain in the full dataset.

### Python API

```python
from inaturalist_interact import INaturalistProjectClient, ProjectDatasetExporter

dataset = INaturalistProjectClient().fetch_project(
    "digital-botanical-gardens-initiative"
)
result = ProjectDatasetExporter().export(dataset, "data/exports/dbgi")
print(result.observation_count)
```

The API client and exporter accept injected collaborators, so unit tests never need
network access.

## Legacy pushing workflow

The existing upload workflow remains available while it is migrated to the new
architecture.

Dry-run the first three uploadable observations from the configured JBP inputs:

```bash
uv run python -m inaturalist_interact.src.pusher --limit 3 --dry-run --verbose
```

### iNaturalist token

For a live upload, the pusher needs an iNaturalist API token for the account that will own the observations.

1. Log in to iNaturalist in a browser.
2. Open <https://www.inaturalist.org/users/api_token>.
3. Copy the token shown on that page.
4. Provide it as `INATURALIST_ACCESS_TOKEN_TODAY`.

You can put it in `inaturalist_interact/src/.env`:

```bash
INATURALIST_ACCESS_TOKEN_TODAY=your_token_here
```

Or export it for the current shell:

```bash
export INATURALIST_ACCESS_TOKEN_TODAY=your_token_here
```

Then pass `--no-dry-run`:

```bash
INATURALIST_ACCESS_TOKEN_TODAY=<token> uv run python -m inaturalist_interact.src.pusher --limit 3 --no-dry-run --verify
```

### Taxon resolution

Before upload, the pusher resolves the CSV taxon name against iNaturalist and sends `taxon_id` when possible. It first tries the full name, then falls back to the genus when the full name is not known to iNaturalist.

For example, `Fascicularia kirchhoffiana` is not an iNaturalist taxon, so the pusher falls back to `Fascicularia` if that genus exists. The original CSV taxon is still preserved in the observation description and tags.

Disable this behavior with:

```bash
uv run python -m inaturalist_interact.src.pusher --no-resolve-taxa
```

## Project wrapper

Use the wrapper script to avoid long copy-paste commands. It takes the project folder name and number of observations to process. Dry-run is the default:

```bash
scripts/push_project.sh jbp-new 3
```

Live upload:

```bash
scripts/push_project.sh jbp-new 20 --live --user dbgi
```

Use `0`, `all`, or `unlimited` as the limit to process all remaining observations allowed by the CSV, state file, and optional curation allow-list.

The wrapper maps `jbp-new` to:

```text
csv:     /media/data/nextcloud_data/emi/files/output/csv/jbp-new
photos:  /media/data/nextcloud_data/emi/files/output/pictures/jbp-new/jbp-new
runtime: /media/data/nextcloud_data/emi/files/output/inat-pusher/jbp-new
```

The runtime directory contains durable upload state and logs.

## Curation allow-lists

For projects with researcher curation reports, first convert the report into a plain `sample_id` allow-list. The Kew report profile accepts rows whose `Notes` value is `OK`, `no photo_05`, or `no photo _05` after normalization:

```bash
scripts/make_allowlist_from_curation.py /path/to/curation.csv --output /media/data/nextcloud_data/emi/files/output/inat-pusher/kew-botanical-gardens/allow_sample_ids.txt
```

The generator defaults to `--profile kew`; use `--id-column`, `--status-column`, and repeated `--accept-status` flags for reports with a different shape.

Then run the project wrapper. If the default allow-list exists in the runtime directory, the wrapper uses it automatically:

```bash
scripts/push_project.sh kew-botanical-gardens 20
```

Live upload:

```bash
scripts/push_project.sh kew-botanical-gardens 20 --live --user dbgi
```

Live upload without a limit:

```bash
scripts/push_project.sh kew-botanical-gardens all --live --user dbgi
```
