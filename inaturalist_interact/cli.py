"""Command-line interface for iNaturalist project interactions."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

from .client import INaturalistProjectClient
from .exporters import ProjectDatasetExporter

DEFAULT_PROJECT = "https://www.inaturalist.org/projects/digital-botanical-gardens-initiative"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(prog="inaturalist-interact")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser(
        "fetch-project",
        help="Retrieve and export all metadata for an iNaturalist project",
    )
    fetch_parser.add_argument(
        "project",
        nargs="?",
        default=DEFAULT_PROJECT,
        help="Project ID, slug, or URL (defaults to the DBGI project)",
    )
    fetch_parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/exports/digital-botanical-gardens-initiative"),
        help="Snapshot output directory",
    )
    fetch_parser.add_argument(
        "--per-page",
        type=int,
        default=200,
        help="iNaturalist API page size (1-200)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface.

    Args:
        argv: Optional argument list. Uses the process arguments when omitted.

    Returns:
        Process exit status.
    """
    args = build_parser().parse_args(argv)
    if args.command == "fetch-project":
        dataset = INaturalistProjectClient(
            per_page=args.per_page,
            access_token=os.getenv("INATURALIST_ACCESS_TOKEN"),
        ).fetch_project(args.project)
        result = ProjectDatasetExporter().export(dataset, args.output)
        print(f"Project: {dataset.project.get('title', dataset.slug)} ({dataset.project_id})")
        print(f"Observations: {result.observation_count}")
        print(f"Observations with DBGI sample IDs: {result.tagged_observation_count}")
        print(f"DBGI sample ID links: {result.sample_link_count}")
        print(f"Unique DBGI sample IDs: {result.unique_sample_id_count}")
        print(f"Sample IDs linked to multiple observations: {result.duplicated_sample_id_count}")
        print(f"Output: {result.output_directory.resolve()}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
