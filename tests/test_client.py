"""Tests for complete and validated iNaturalist project retrieval."""

from datetime import UTC, datetime
from typing import Any

import pytest

from inaturalist_interact.client import (
    INaturalistProjectClient,
    IncompleteDatasetError,
    InvalidApiResponseError,
    ProjectNotFoundError,
)


class FakeProjectApi:
    """Record fake API calls and return deterministic paginated responses."""

    def __init__(self) -> None:
        """Initialize call tracking."""
        self.project_calls: list[tuple[object, bool]] = []
        self.observation_calls: list[dict[str, Any]] = []

    def get_project(self, project_id: object, *, rule_details: bool) -> dict[str, Any]:
        """Return one project response."""
        self.project_calls.append((project_id, rule_details))
        return {"total_results": 1, "results": [{"id": 130644, "slug": "dbgi", "title": "DBGI"}]}

    def get_observations(self, **kwargs: Any) -> dict[str, Any]:
        """Return two pages with rich observation values."""
        self.observation_calls.append(kwargs)
        pages = {
            1: [
                {"id": 10, "tags": ["emi_external_id:dbgi_000010"], "taxon": {"id": 1}},
                {"id": 11, "tags": [], "photos": [{"id": 2}]},
            ],
            2: [{"id": 12, "tags": ["dbgi_000012"], "ofvs": [{"value": "metadata"}]}],
        }
        return {"total_results": 3, "results": pages[kwargs["page"]]}


def test_fetch_project_retrieves_all_pages_and_preserves_metadata() -> None:
    """The client should explicitly paginate and retain nested API metadata."""
    api = FakeProjectApi()
    timestamp = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)
    client = INaturalistProjectClient(
        per_page=2,
        project_getter=api.get_project,
        observation_getter=api.get_observations,
        clock=lambda: timestamp,
    )

    dataset = client.fetch_project("https://www.inaturalist.org/projects/dbgi")

    assert api.project_calls == [("dbgi", True)]
    assert [call["page"] for call in api.observation_calls] == [1, 2]
    assert all(call["project_id"] == 130644 for call in api.observation_calls)
    assert all(call["order_by"] == "id" for call in api.observation_calls)
    assert dataset.reported_total == 3
    assert dataset.retrieved_at == timestamp
    assert [observation["id"] for observation in dataset.observations] == [10, 11, 12]
    assert dataset.observations[2]["ofvs"] == [{"value": "metadata"}]


def test_client_validates_page_size() -> None:
    """Page sizes outside the documented API range should fail locally."""
    with pytest.raises(ValueError, match="between 1 and 200"):
        INaturalistProjectClient(per_page=201)


def test_fetch_project_passes_access_token_when_configured() -> None:
    """Authenticated retrieval should pass its token to observation requests."""
    requests: list[dict[str, Any]] = []
    client = INaturalistProjectClient(
        access_token="secret",
        project_getter=lambda *args, **kwargs: {"results": [{"id": 1}]},
        observation_getter=lambda **kwargs: requests.append(kwargs)
        or {"total_results": 0, "results": []},
    )

    client.fetch_project(1)

    assert requests[0]["access_token"] == "secret"


def test_fetch_project_reports_missing_project() -> None:
    """An empty project response should produce a domain-specific error."""
    client = INaturalistProjectClient(
        project_getter=lambda *args, **kwargs: {"total_results": 0, "results": []},
        observation_getter=lambda **kwargs: {"total_results": 0, "results": []},
    )

    with pytest.raises(ProjectNotFoundError):
        client.fetch_project("missing")


def test_fetch_project_rejects_duplicate_observation_ids() -> None:
    """Duplicate IDs across API pages should not silently corrupt a snapshot."""
    responses = iter(
        [
            {"total_results": 2, "results": [{"id": 1}]},
            {"total_results": 2, "results": [{"id": 1}]},
        ]
    )
    client = INaturalistProjectClient(
        per_page=1,
        project_getter=lambda *args, **kwargs: {"results": [{"id": 1}]},
        observation_getter=lambda **kwargs: next(responses),
    )

    with pytest.raises(InvalidApiResponseError, match="Duplicate"):
        client.fetch_project(1)


def test_fetch_project_rejects_incomplete_last_page() -> None:
    """A short response below the API total should fail rather than look complete."""
    client = INaturalistProjectClient(
        per_page=2,
        project_getter=lambda *args, **kwargs: {"results": [{"id": 1}]},
        observation_getter=lambda **kwargs: {"total_results": 3, "results": [{"id": 1}]},
    )

    with pytest.raises(IncompleteDatasetError, match="Retrieved 1"):
        client.fetch_project(1)


@pytest.mark.parametrize("response", [None, {}, {"results": None}, {"results": ["invalid"]}])
def test_fetch_project_rejects_malformed_project_responses(response: object) -> None:
    """Unexpected API response shapes should raise a clear validation error."""
    client = INaturalistProjectClient(
        project_getter=lambda *args, **kwargs: response,  # type: ignore[return-value]
        observation_getter=lambda **kwargs: {"total_results": 0, "results": []},
    )

    with pytest.raises(InvalidApiResponseError):
        client.fetch_project(1)
