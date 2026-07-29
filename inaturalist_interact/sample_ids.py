"""Extraction of DBGI sample identifiers from iNaturalist observation tags."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any


class DbgiSampleIdExtractor:
    """Extract canonical ``dbgi_XXXXXX`` identifiers from observation tags."""

    def __init__(self, pattern: str = r"(?<![A-Za-z0-9])dbgi_(\d{6})(?!\d)") -> None:
        """Create an extractor.

        Args:
            pattern: Regular expression containing the six digits in its first
                capture group. Matching is case-insensitive.
        """
        self._pattern = re.compile(pattern, flags=re.IGNORECASE)

    def extract(self, tags: Iterable[object] | None) -> tuple[str, ...]:
        """Return unique sample IDs found in tags, sorted canonically.

        Tags such as ``dbgi_001353`` and
        ``emi_external_id:DBGI_001353`` both produce ``dbgi_001353``.

        Args:
            tags: Tag values returned by iNaturalist.

        Returns:
            A sorted tuple of normalized sample IDs.
        """
        matches = {
            f"dbgi_{match.group(1)}"
            for tag in tags or ()
            if isinstance(tag, str)
            for match in self._pattern.finditer(tag)
        }
        return tuple(sorted(matches))

    def extract_from_observation(self, observation: Mapping[str, Any]) -> tuple[str, ...]:
        """Extract sample IDs from an observation's ``tags`` field.

        Args:
            observation: Raw iNaturalist observation mapping.

        Returns:
            A sorted tuple of normalized sample IDs.
        """
        tags = observation.get("tags")
        return self.extract(tags if isinstance(tags, list | tuple | set) else None)

    def matching_tags(self, observation: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
        """Map each sample ID to the exact tags in which it occurs.

        Args:
            observation: Raw iNaturalist observation mapping.

        Returns:
            A mapping from canonical sample ID to matching original tag strings.
        """
        matches: dict[str, set[str]] = {}
        tags = observation.get("tags")
        if not isinstance(tags, list | tuple | set):
            return {}

        for tag in tags:
            if not isinstance(tag, str):
                continue
            for match in self._pattern.finditer(tag):
                sample_id = f"dbgi_{match.group(1)}"
                matches.setdefault(sample_id, set()).add(tag)
        return {sample_id: tuple(sorted(values)) for sample_id, values in sorted(matches.items())}

