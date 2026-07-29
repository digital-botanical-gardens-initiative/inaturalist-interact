"""Lossless and tabular exporters for retrieved iNaturalist datasets."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, TextIO
from uuid import UUID

from .models import ProjectDataset
from .sample_ids import DbgiSampleIdExtractor


@dataclass(frozen=True, slots=True)
class ExportResult:
    """Paths and counts produced by a project export."""

    output_directory: Path
    project_file: Path
    observations_file: Path
    observations_csv_file: Path
    sample_links_file: Path
    manifest_file: Path
    observation_count: int
    tagged_observation_count: int
    sample_link_count: int
    unique_sample_id_count: int
    duplicated_sample_id_count: int


class ProjectDatasetExporter:
    """Export a project snapshot to lossless JSON and analysis-friendly CSV."""

    FORMAT_VERSION = 1

    def __init__(self, sample_id_extractor: DbgiSampleIdExtractor | None = None) -> None:
        """Create an exporter.

        Args:
            sample_id_extractor: Strategy used to associate DBGI sample IDs with
                observations. Defaults to :class:`DbgiSampleIdExtractor`.
        """
        self._sample_ids = sample_id_extractor or DbgiSampleIdExtractor()

    def export(self, dataset: ProjectDataset, output_directory: Path | str) -> ExportResult:
        """Write a complete, deterministic project snapshot.

        The export contains:

        * ``project.json``: complete project metadata;
        * ``observations.jsonl``: one complete API observation per line;
        * ``observations.csv``: every top-level observation field, with nested
          values encoded as JSON and derived DBGI sample-ID columns;
        * ``sample_id_links.csv``: one observation/sample association per row;
        * ``manifest.json``: snapshot provenance and summary counts.

        Existing files with these names are replaced atomically.

        Args:
            dataset: Complete dataset returned by the project client.
            output_directory: Directory in which snapshot files are created.

        Returns:
            Paths and summary counts for the exported snapshot.
        """
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)
        project_file = output / "project.json"
        observations_file = output / "observations.jsonl"
        observations_csv_file = output / "observations.csv"
        sample_links_file = output / "sample_id_links.csv"
        manifest_file = output / "manifest.json"

        sample_matches = [self._sample_ids.matching_tags(observation) for observation in dataset.observations]
        tagged_observation_count = sum(bool(matches) for matches in sample_matches)
        sample_link_count = sum(len(matches) for matches in sample_matches)
        sample_id_counts = Counter(sample_id for matches in sample_matches for sample_id in matches)
        unique_sample_id_count = len(sample_id_counts)
        duplicated_sample_id_count = sum(count > 1 for count in sample_id_counts.values())

        self._write_json(project_file, dataset.project)
        self._write_json_lines(observations_file, dataset.observations)
        self._write_observation_csv(observations_csv_file, dataset.observations, sample_matches)
        self._write_sample_links(sample_links_file, dataset.observations, sample_matches)

        manifest = {
            "format_version": self.FORMAT_VERSION,
            "project_id": dataset.project_id,
            "project_slug": dataset.slug,
            "project_reference": str(dataset.reference),
            "retrieved_at": dataset.retrieved_at,
            "api_reported_observation_count": dataset.reported_total,
            "exported_observation_count": len(dataset.observations),
            "observations_with_dbgi_sample_ids": tagged_observation_count,
            "dbgi_sample_id_links": sample_link_count,
            "unique_dbgi_sample_ids": unique_sample_id_count,
            "dbgi_sample_ids_linked_to_multiple_observations": duplicated_sample_id_count,
            "files": {
                "project": project_file.name,
                "observations_jsonl": observations_file.name,
                "observations_csv": observations_csv_file.name,
                "sample_id_links_csv": sample_links_file.name,
            },
        }
        self._write_json(manifest_file, manifest)

        return ExportResult(
            output_directory=output,
            project_file=project_file,
            observations_file=observations_file,
            observations_csv_file=observations_csv_file,
            sample_links_file=sample_links_file,
            manifest_file=manifest_file,
            observation_count=len(dataset.observations),
            tagged_observation_count=tagged_observation_count,
            sample_link_count=sample_link_count,
            unique_sample_id_count=unique_sample_id_count,
            duplicated_sample_id_count=duplicated_sample_id_count,
        )

    def _write_json(self, path: Path, value: object) -> None:
        """Atomically write a pretty-printed JSON document."""
        self._atomic_write(path, lambda handle: json.dump(value, handle, **_json_dump_options(indent=2)))

    def _write_json_lines(self, path: Path, observations: Sequence[Mapping[str, Any]]) -> None:
        """Atomically write complete observations as JSON Lines."""

        def write(handle: TextIO) -> None:
            """Write JSON Lines content to an open temporary file."""
            for observation in observations:
                handle.write(json.dumps(observation, **_json_dump_options()))
                handle.write("\n")

        self._atomic_write(path, write)

    def _write_observation_csv(
        self,
        path: Path,
        observations: Sequence[Mapping[str, Any]],
        sample_matches: Sequence[Mapping[str, tuple[str, ...]]],
    ) -> None:
        """Atomically write all top-level observation fields as CSV."""
        api_fields = sorted({key for observation in observations for key in observation})
        derived_fields = ["dbgi_sample_ids", "dbgi_sample_id_count"]
        fieldnames = [*api_fields, *derived_fields]

        def write(handle: TextIO) -> None:
            """Write flattened observation rows to an open temporary file."""
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for observation, matches in zip(observations, sample_matches, strict=True):
                row = {key: _csv_value(observation.get(key)) for key in api_fields}
                row["dbgi_sample_ids"] = "|".join(matches)
                row["dbgi_sample_id_count"] = len(matches)
                writer.writerow(row)

        self._atomic_write(path, write)

    def _write_sample_links(
        self,
        path: Path,
        observations: Sequence[Mapping[str, Any]],
        sample_matches: Sequence[Mapping[str, tuple[str, ...]]],
    ) -> None:
        """Atomically write one row per DBGI sample/observation association."""
        fieldnames = ["sample_id", "observation_id", "observation_uri", "matching_tags"]

        def write(handle: TextIO) -> None:
            """Write sample/observation link rows to an open temporary file."""
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for observation, matches in zip(observations, sample_matches, strict=True):
                for sample_id, tags in matches.items():
                    writer.writerow(
                        {
                            "sample_id": sample_id,
                            "observation_id": observation.get("id", ""),
                            "observation_uri": observation.get("uri", ""),
                            "matching_tags": json.dumps(tags, ensure_ascii=False),
                        }
                    )

        self._atomic_write(path, write)

    @staticmethod
    def _atomic_write(path: Path, writer: Callable[[TextIO], None]) -> None:
        """Write a text file through a temporary sibling and atomically replace it."""
        file_descriptor, temporary_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", text=True)
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
                writer(handle)
            Path(temporary_name).replace(path)
        except BaseException:
            Path(temporary_name).unlink(missing_ok=True)
            raise


def _json_default(value: object) -> str | list[object]:
    """Convert supported non-JSON API values to deterministic representations."""
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, set | tuple):
        return list(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _json_dump_options(*, indent: int | None = None) -> dict[str, Any]:
    """Return consistent keyword arguments for JSON serialization."""
    return {
        "default": _json_default,
        "ensure_ascii": False,
        "indent": indent,
        "sort_keys": True,
    }


def _csv_value(value: object) -> object:
    """Convert one API value to a lossless-enough CSV cell representation."""
    if value is None:
        return ""
    if isinstance(value, str | int | float | bool):
        return value
    return json.dumps(value, **_json_dump_options())
