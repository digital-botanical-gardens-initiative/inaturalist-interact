"""Tests for DBGI sample-ID extraction from iNaturalist tags."""

from inaturalist_interact.sample_ids import DbgiSampleIdExtractor


def test_extract_finds_plain_and_prefixed_tags() -> None:
    """Plain and namespaced tags should yield canonical sample IDs."""
    extractor = DbgiSampleIdExtractor()

    assert extractor.extract(
        [
            "dbgi_001353",
            "emi_external_id:DBGI_008572",
            "unrelated",
            "source dbgi_001353",
        ]
    ) == ("dbgi_001353", "dbgi_008572")


def test_extract_requires_exactly_six_digits() -> None:
    """Shorter IDs and IDs followed by another digit should not match."""
    extractor = DbgiSampleIdExtractor()

    assert extractor.extract(["dbgi_12345", "dbgi_1234567", "xdbgi_123456"]) == ()


def test_extract_ignores_missing_or_malformed_tags() -> None:
    """Absent tags and non-string values should be ignored safely."""
    extractor = DbgiSampleIdExtractor()

    assert extractor.extract(None) == ()
    assert extractor.extract([None, 123, {"tag": "dbgi_001353"}]) == ()
    assert extractor.extract_from_observation({"tags": "dbgi_001353"}) == ()


def test_matching_tags_preserves_original_tag_text() -> None:
    """Association output should retain every source tag for traceability."""
    extractor = DbgiSampleIdExtractor()
    observation = {
        "tags": [
            "DBGI_001353",
            "emi_external_id:dbgi_001353",
            "emi_external_id:dbgi_008572",
        ]
    }

    assert extractor.matching_tags(observation) == {
        "dbgi_001353": ("DBGI_001353", "emi_external_id:dbgi_001353"),
        "dbgi_008572": ("emi_external_id:dbgi_008572",),
    }

