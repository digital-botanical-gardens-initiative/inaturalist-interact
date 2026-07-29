"""Domain models used by the iNaturalist project retrieval pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlparse


class InvalidProjectReferenceError(ValueError):
    """Raised when a project reference cannot be converted to an API identifier."""


@dataclass(frozen=True, slots=True)
class ProjectReference:
    """A validated iNaturalist project ID or slug."""

    value: int | str

    @classmethod
    def parse(cls, value: int | str) -> ProjectReference:
        """Parse a numeric ID, slug, or iNaturalist project URL.

        Args:
            value: Project ID, project slug, or URL whose path starts with
                ``/projects/``.

        Returns:
            A normalized project reference suitable for ``pyinaturalist``.

        Raises:
            InvalidProjectReferenceError: If the value is empty or is not a
                recognizable iNaturalist project reference.
        """
        if isinstance(value, int):
            if value <= 0:
                raise InvalidProjectReferenceError("Project IDs must be positive")
            return cls(value)

        candidate = value.strip()
        if not candidate:
            raise InvalidProjectReferenceError("Project reference cannot be empty")
        if candidate.isdecimal():
            return cls(int(candidate))

        parsed = urlparse(candidate)
        if parsed.scheme or parsed.netloc:
            if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {
                "inaturalist.org",
                "www.inaturalist.org",
            }:
                raise InvalidProjectReferenceError(f"Not an iNaturalist project URL: {candidate}")
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) < 2 or path_parts[0] != "projects":
                raise InvalidProjectReferenceError(f"Not an iNaturalist project URL: {candidate}")
            candidate = path_parts[1]

        if any(character.isspace() for character in candidate) or "/" in candidate:
            raise InvalidProjectReferenceError(f"Invalid iNaturalist project slug: {candidate}")
        return cls(candidate)

    def __str__(self) -> str:
        """Return the normalized API value as text."""
        return str(self.value)


@dataclass(frozen=True, slots=True)
class ProjectDataset:
    """A complete project response and all retrieved observation responses."""

    reference: ProjectReference
    project: dict[str, Any]
    observations: tuple[dict[str, Any], ...]
    retrieved_at: datetime
    reported_total: int

    @property
    def project_id(self) -> int:
        """Return the numeric iNaturalist project ID.

        Raises:
            TypeError: If the project response has no numeric ``id``.
        """
        project_id = self.project.get("id")
        if not isinstance(project_id, int):
            raise TypeError("Project metadata does not contain a numeric id")
        return project_id

    @property
    def slug(self) -> str:
        """Return the project slug, falling back to its numeric ID."""
        slug = self.project.get("slug")
        return slug if isinstance(slug, str) and slug else str(self.project_id)
