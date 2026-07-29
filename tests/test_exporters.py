"""Tests for lossless project snapshot exports."""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from inaturalist_interact.exporters import ProjectDatasetExporter
from inaturalist_interact.models import ProjectDataset, ProjectReference


def make_dataset() -> ProjectDataset:
    """Create a representative dataset with nested metadata and tag links."""
    return ProjectDataset(
        reference=ProjectReference("dbgi"),
        project={"id": 130644, "slug": "dbgi", "title": "DBGI"},
        observations=(
            {
                "id": 10,
                "uri": "https://www.inaturalist.org/observations/10",
                "created_at": datetime(2026, 1, 2, 3, 4, tzinfo=UTC),
                "tags": ["emi_external_id:dbgi_000010", "curated"],
                "taxon": {"id": 42, "name": "Silene"},
                "photos": [{"id": 99, "license_code": "cc-by"}],
            },
            {
                "id": 11,
                "uri": "https://www.inaturalist.org/observations/11",
                "tags": ["dbgi_000011", "also DBGI_000012"],
                "taxon": None,
            },
            {"id": 12, "uri": "https://www.inaturalist.org/observations/12", "tags": []},
        ),
        retrieved_at=datetime(2026, 7, 29, 12, 0, tzinfo=UTC),
        reported_total=3,
    )


def test_export_writes_complete_snapshot_and_summary(tmp_path: Path) -> None:
    """Exporter should write all formats and accurate association counts."""
    result = ProjectDatasetExporter().export(make_dataset(), tmp_path)

    assert result.observation_count == 3
    assert result.tagged_observation_count == 2
    assert result.sample_link_count == 3
    assert result.unique_sample_id_count == 3
    assert result.duplicated_sample_id_count == 0
    assert result.project_file.exists()
    assert result.observations_file.exists()
    assert result.observations_csv_file.exists()
    assert result.sample_links_file.exists()
    assert result.manifest_file.exists()

    manifest = json.loads(result.manifest_file.read_text())
    assert manifest["project_id"] == 130644
    assert manifest["exported_observation_count"] == 3
    assert manifest["observations_with_dbgi_sample_ids"] == 2
    assert manifest["dbgi_sample_id_links"] == 3
    assert manifest["unique_dbgi_sample_ids"] == 3
    assert manifest["dbgi_sample_ids_linked_to_multiple_observations"] == 0


def test_json_lines_preserves_nested_metadata_and_dates(tmp_path: Path) -> None:
    """JSON Lines should retain nested API values and serialize timestamps."""
    result = ProjectDatasetExporter().export(make_dataset(), tmp_path)
    records = [json.loads(line) for line in result.observations_file.read_text().splitlines()]

    assert records[0]["taxon"] == {"id": 42, "name": "Silene"}
    assert records[0]["photos"] == [{"id": 99, "license_code": "cc-by"}]
    assert records[0]["created_at"] == "2026-01-02T03:04:00+00:00"
    assert records[0]["tags"] == ["emi_external_id:dbgi_000010", "curated"]


def test_observation_csv_contains_all_top_level_fields_and_sample_ids(tmp_path: Path) -> None:
    """Observation CSV should include dynamic API fields and derived ID columns."""
    result = ProjectDatasetExporter().export(make_dataset(), tmp_path)
    with result.observations_csv_file.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 3
    assert json.loads(rows[0]["taxon"]) == {"id": 42, "name": "Silene"}
    assert json.loads(rows[0]["tags"]) == ["emi_external_id:dbgi_000010", "curated"]
    assert rows[0]["dbgi_sample_ids"] == "dbgi_000010"
    assert rows[1]["dbgi_sample_ids"] == "dbgi_000011|dbgi_000012"
    assert rows[2]["dbgi_sample_id_count"] == "0"


def test_sample_links_include_original_matching_tags(tmp_path: Path) -> None:
    """Link CSV should retain the tag text that established each association."""
    result = ProjectDatasetExporter().export(make_dataset(), tmp_path)
    with result.sample_links_file.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert [row["sample_id"] for row in rows] == ["dbgi_000010", "dbgi_000011", "dbgi_000012"]
    assert json.loads(rows[0]["matching_tags"]) == ["emi_external_id:dbgi_000010"]
    assert rows[0]["observation_id"] == "10"


def test_export_replaces_existing_files(tmp_path: Path) -> None:
    """Repeated snapshots should replace stale output instead of appending."""
    exporter = ProjectDatasetExporter()
    exporter.export(make_dataset(), tmp_path)
    (tmp_path / "observations.jsonl").write_text("stale\n")

    result = exporter.export(make_dataset(), tmp_path)

    assert "stale" not in result.observations_file.read_text()
    assert len(result.observations_file.read_text().splitlines()) == 3
