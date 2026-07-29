"""Client for retrieving complete iNaturalist project metadata."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from pyinaturalist import get_observations, get_projects_by_id

from .models import ProjectDataset, ProjectReference

ProjectGetter = Callable[..., dict[str, Any]]
ObservationGetter = Callable[..., dict[str, Any]]


class INaturalistRetrievalError(RuntimeError):
    """Base exception for invalid or incomplete iNaturalist API responses."""


class ProjectNotFoundError(INaturalistRetrievalError):
    """Raised when iNaturalist returns no project for a reference."""


class InvalidApiResponseError(INaturalistRetrievalError):
    """Raised when an iNaturalist response does not have the expected shape."""


class IncompleteDatasetError(INaturalistRetrievalError):
    """Raised when pagination ends before the API-reported observation total."""


class INaturalistProjectClient:
    """Retrieve project metadata and every project observation via pyinaturalist."""

    def __init__(
        self,
        *,
        per_page: int = 200,
        project_getter: ProjectGetter = get_projects_by_id,
        observation_getter: ObservationGetter = get_observations,
        clock: Callable[[], datetime] | None = None,
        access_token: str | None = None,
    ) -> None:
        """Configure the project client.

        Args:
            per_page: Number of observations requested per API page. iNaturalist
                currently permits at most 200.
            project_getter: Injectable project endpoint, primarily for tests.
            observation_getter: Injectable observation endpoint, primarily for
                tests.
            clock: Injectable UTC clock used to timestamp snapshots.
            access_token: Optional iNaturalist access token. Supplying one allows
                the API to return metadata visible to its owner.

        Raises:
            ValueError: If ``per_page`` is outside the iNaturalist API range.
        """
        if not 1 <= per_page <= 200:
            raise ValueError("per_page must be between 1 and 200")
        self._per_page = per_page
        self._project_getter = project_getter
        self._observation_getter = observation_getter
        self._clock = clock or (lambda: datetime.now(UTC))
        self._access_token = access_token

    def fetch_project(self, reference: ProjectReference | int | str) -> ProjectDataset:
        """Retrieve project metadata and all associated observations.

        Observations are requested in ascending ID order with explicit
        pagination. Duplicate observation IDs are rejected because they would
        make the exported snapshot ambiguous.

        Args:
            reference: Parsed reference, numeric ID, slug, or project URL.

        Returns:
            A complete in-memory project snapshot.

        Raises:
            ProjectNotFoundError: If the project does not exist.
            InvalidApiResponseError: If an API response is malformed.
            IncompleteDatasetError: If fewer unique observations are returned
                than the API reports.
        """
        parsed_reference = (
            reference if isinstance(reference, ProjectReference) else ProjectReference.parse(reference)
        )
        project = self._fetch_project_metadata(parsed_reference)
        project_id = project.get("id")
        if not isinstance(project_id, int):
            raise InvalidApiResponseError("Project response is missing a numeric id")

        observations, reported_total = self._fetch_observations(project_id)
        return ProjectDataset(
            reference=parsed_reference,
            project=project,
            observations=tuple(observations),
            retrieved_at=self._clock(),
            reported_total=reported_total,
        )

    def _fetch_project_metadata(self, reference: ProjectReference) -> dict[str, Any]:
        """Retrieve and validate one project's metadata response."""
        response = self._project_getter(reference.value, rule_details=True)
        results = self._response_results(response, endpoint="projects")
        if not results:
            raise ProjectNotFoundError(f"iNaturalist project not found: {reference}")
        return dict(results[0])

    def _fetch_observations(self, project_id: int) -> tuple[list[dict[str, Any]], int]:
        """Retrieve and validate every observation page for a project."""
        observations: list[dict[str, Any]] = []
        seen_ids: set[int] = set()
        page = 1
        reported_total = 0

        while True:
            request = {
                "project_id": project_id,
                "page": page,
                "per_page": self._per_page,
                "order": "asc",
                "order_by": "id",
            }
            if self._access_token:
                request["access_token"] = self._access_token
            response = self._observation_getter(**request)
            results = self._response_results(response, endpoint="observations")
            total = response.get("total_results")
            if not isinstance(total, int) or total < 0:
                raise InvalidApiResponseError("Observation response has an invalid total_results")
            reported_total = total

            for result in results:
                observation_id = result.get("id")
                if not isinstance(observation_id, int):
                    raise InvalidApiResponseError("Observation response is missing a numeric id")
                if observation_id in seen_ids:
                    raise InvalidApiResponseError(f"Duplicate observation id returned: {observation_id}")
                seen_ids.add(observation_id)
                observations.append(dict(result))

            if len(results) < self._per_page or len(observations) >= reported_total:
                break
            page += 1

        if len(observations) < reported_total:
            raise IncompleteDatasetError(
                f"Retrieved {len(observations)} observations but iNaturalist reported {reported_total}"
            )
        return observations, reported_total

    @staticmethod
    def _response_results(response: object, *, endpoint: str) -> list[Mapping[str, Any]]:
        """Return a validated ``results`` list from an API response."""
        if not isinstance(response, Mapping):
            raise InvalidApiResponseError(f"{endpoint} endpoint returned a non-mapping response")
        results = response.get("results")
        if not isinstance(results, list) or not all(isinstance(result, Mapping) for result in results):
            raise InvalidApiResponseError(f"{endpoint} endpoint returned an invalid results list")
        return results
