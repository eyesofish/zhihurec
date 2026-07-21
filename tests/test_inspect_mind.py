from __future__ import annotations

from pathlib import Path

from scripts.inspect_mind import EXPECTED_SCALE, inspect_dataset, parse_candidate


def _write_split(
    root: Path,
    split: str,
    *,
    news_rows: list[str],
    behavior_rows: list[str],
) -> None:
    split_root = root / "small" / split
    split_root.mkdir(parents=True)
    (split_root / "news.tsv").write_text("\n".join(news_rows) + "\n", encoding="utf-8")
    (split_root / "behaviors.tsv").write_text(
        "\n".join(behavior_rows) + "\n",
        encoding="utf-8",
    )


def test_inspector_reports_overlap_counts_and_split_strategy(tmp_path: Path):
    news_rows = [
        "N1\tnews\tlocal\tOne\tFirst abstract\thttps://example.com/1\t[]\t[]",
        "N2\tsports\tgolf\tTwo\t\thttps://example.com/2\t[]\t[]",
        "N3\tfinance\tmarkets\tThree\tThird abstract\thttps://example.com/3\t[]\t[]",
    ]
    _write_split(
        tmp_path,
        "train",
        news_rows=news_rows,
        behavior_rows=[
            "1\tU1\t11/13/2019 8:36:57 AM\tN1\tN1-0 N2-1",
            "2\tU2\t11/13/2019 9:36:57 AM\t\tN3-1 N2-1",
        ],
    )
    _write_split(
        tmp_path,
        "dev",
        news_rows=news_rows,
        behavior_rows=[
            "1\tU1\t11/14/2019 8:36:57 AM\tN2\tN1-1 N3-0",
        ],
    )

    report = inspect_dataset(variant="small", raw_root=tmp_path, validate_scale=False)

    assert report["validation"]["passed"] is True
    assert report["splits"]["train"]["behaviors"]["candidates"] == 4
    assert report["splits"]["train"]["behaviors"]["positives"] == 3
    assert report["splits"]["train"]["behaviors"]["requests_with_multiple_positives"] == 1
    assert report["splits"]["train"]["news"]["empty_field_ratio"]["abstract"] == 0.333333
    assert report["overlap"]["users"] == 1
    assert report["overlap"]["raw_impression_ids"] == 1
    assert (
        report["recommended_als_evaluation_strategy"]
        == "official_dev_known_user_with_cold_start_segment"
    )


def test_inspector_rejects_missing_metadata_and_malformed_ids(tmp_path: Path):
    _write_split(
        tmp_path,
        "train",
        news_rows=[
            "bad\tnews\tlocal\tOne\tAbstract\thttps://example.com/1\t[]\t[]",
            "N1\tnews\tlocal\tOne\tAbstract\thttps://example.com/1\t[]\t[]",
        ],
        behavior_rows=[
            "1\tU1\t11/13/2019 8:36:57 AM\tN404\tN1-1 N404-0",
            "2\tbad-user\tbad-time\t\tbroken",
        ],
    )

    report = inspect_dataset(
        variant="small",
        raw_root=tmp_path,
        splits=("train",),
        validate_scale=False,
    )

    assert report["validation"]["passed"] is False
    assert any("invalid news ID" in error for error in report["validation"]["errors"])
    assert any(
        "candidate news IDs lack metadata" in error for error in report["validation"]["errors"]
    )
    assert any(
        "history news IDs lack metadata" in error for error in report["validation"]["errors"]
    )
    assert any("invalid user ID" in error for error in report["validation"]["errors"])


def test_candidate_parser_supports_binary_labels():
    assert parse_candidate("N123-0") == ("N123", 0)
    assert parse_candidate("N123-1") == ("N123", 1)


def test_large_dev_scale_accepts_the_published_behavior_count():
    lower, upper = EXPECTED_SCALE[("large", "dev")]["behaviors"]

    assert lower <= 376_471 <= upper
