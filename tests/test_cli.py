"""Tests for the retrieval command-line interface."""

from pathlib import Path

from inaturalist_interact.cli import DEFAULT_PROJECT, build_parser


def test_fetch_project_defaults_to_dbgi_project() -> None:
    """The shortest command should target the canonical DBGI project."""
    args = build_parser().parse_args(["fetch-project"])

    assert args.project == DEFAULT_PROJECT
    assert args.per_page == 200
    assert args.output == Path("data/exports/digital-botanical-gardens-initiative")


def test_fetch_project_accepts_slug_and_output() -> None:
    """CLI users should be able to select another project and output path."""
    args = build_parser().parse_args(["fetch-project", "another-project", "--output", "snapshot"])

    assert args.project == "another-project"
    assert args.output == Path("snapshot")
