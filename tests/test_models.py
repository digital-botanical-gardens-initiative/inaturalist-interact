"""Tests for project reference and dataset domain models."""

from datetime import UTC, datetime

import pytest

from inaturalist_interact.models import (
    InvalidProjectReferenceError,
    ProjectDataset,
    ProjectReference,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (130644, 130644),
        ("130644", 130644),
        ("digital-botanical-gardens-initiative", "digital-botanical-gardens-initiative"),
        (
            "https://www.inaturalist.org/projects/digital-botanical-gardens-initiative",
            "digital-botanical-gardens-initiative",
        ),
        (
            "https://inaturalist.org/projects/digital-botanical-gardens-initiative?tab=about",
            "digital-botanical-gardens-initiative",
        ),
    ],
)
def test_project_reference_parse_accepts_supported_forms(raw: int | str, expected: int | str) -> None:
    """Supported project references should normalize to one API value."""
    assert ProjectReference.parse(raw).value == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        " ",
        0,
        -1,
        "https://example.org/projects/dbgi",
        "https://www.inaturalist.org/observations/1",
        "invalid slug",
    ],
)
def test_project_reference_parse_rejects_invalid_values(raw: int | str) -> None:
    """Invalid IDs, URLs, and slugs should fail before an API request."""
    with pytest.raises(InvalidProjectReferenceError):
        ProjectReference.parse(raw)


def test_project_dataset_exposes_project_identity() -> None:
    """Dataset helpers should expose the canonical project ID and slug."""
    dataset = ProjectDataset(
        reference=ProjectReference(130644),
        project={"id": 130644, "slug": "dbgi"},
        observations=(),
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        reported_total=0,
    )

    assert dataset.project_id == 130644
    assert dataset.slug == "dbgi"


def test_project_dataset_rejects_missing_numeric_project_id() -> None:
    """A malformed project response should not produce a fake identity."""
    dataset = ProjectDataset(
        reference=ProjectReference("dbgi"),
        project={"slug": "dbgi"},
        observations=(),
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        reported_total=0,
    )

    with pytest.raises(TypeError, match="numeric id"):
        _ = dataset.project_id
