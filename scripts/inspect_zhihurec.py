#!/usr/bin/env python3
"""Inspect the official ZhihuRec-1M split derived from the THUIR release.

This script:
1. Reads the eight CSV tables under data/zhihurec_1m/raw by default.
2. Prints the README field meanings for each table.
3. Checks primary-key uniqueness for the six entity tables.
4. Samples foreign-key style relationships across users, answers, questions,
   authors, topics, and tokens.
5. Prints a short summary of which tables can be joined to which tables.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple


TABLE_ORDER = [
    "inter_impression.csv",
    "inter_query.csv",
    "info_user.csv",
    "info_answer.csv",
    "info_question.csv",
    "info_author.csv",
    "info_topic.csv",
    "info_token.csv",
]


FIELD_DOCS: Dict[str, List[Tuple[int, bool, str]]] = {
    "inter_impression.csv": [
        (0, False, "user ID"),
        (1, False, "answer ID"),
        (2, False, "impression timestamp"),
        (3, False, "click timestamp (0 for non-click)"),
    ],
    "inter_query.csv": [
        (0, False, "user ID"),
        (1, False, "token IDs in the query (separated by spaces)"),
        (2, False, "query timestamp"),
    ],
    "info_user.csv": [
        (0, False, "user ID"),
        (1, False, "register timestamp"),
        (2, False, "gender"),
        (3, False, "login frequency"),
        (4, False, "#followers"),
        (5, False, "#topics followed by this user"),
        (6, False, "#questions followed by this user"),
        (7, False, "#answers"),
        (8, False, "#questions"),
        (9, False, "#comments"),
        (10, False, "#thanks received by this user"),
        (11, False, "#comments received by this user"),
        (12, False, "#likes received by this user"),
        (13, False, "#dislikes received by this user"),
        (14, False, "register type"),
        (15, False, "register platform"),
        (16, False, "from android or not"),
        (17, False, "from iphone or not"),
        (18, False, "from ipad or not"),
        (19, False, "from pc or not"),
        (20, False, "from mobile web or not"),
        (21, False, "device model"),
        (22, False, "device brand"),
        (23, False, "platform"),
        (24, False, "province"),
        (25, False, "city"),
        (26, False, "topic IDs followed by this user (separated by spaces)"),
    ],
    "info_answer.csv": [
        (0, False, "answer ID"),
        (1, True, "question ID"),
        (2, False, "anonymous or not"),
        (3, True, "author ID (null for anonymous)"),
        (4, False, "labeled high-value answer or not"),
        (5, False, "recommended by the editor or not"),
        (6, False, "create timestamp"),
        (7, False, "contain pictures or not"),
        (8, False, "contain videos or not"),
        (9, False, "#thanks"),
        (10, False, "#likes"),
        (11, False, "#comments"),
        (12, False, "#collections"),
        (13, False, "#dislikes"),
        (14, False, "#reports"),
        (15, False, "#helpless"),
        (16, True, "token IDs in the answer (separated by spaces)"),
        (17, True, "topic IDs of the answer (separated by spaces)"),
    ],
    "info_question.csv": [
        (0, False, "question ID"),
        (1, False, "create timestamp"),
        (2, False, "#answers"),
        (3, False, "#followers"),
        (4, False, "#invitations"),
        (5, False, "#comments"),
        (6, True, "token IDs in the question (separated by spaces)"),
        (7, True, "topic IDs of the question (separated by spaces)"),
    ],
    "info_author.csv": [
        (0, False, "author ID"),
        (1, False, "is excellent author or not"),
        (2, False, "#followers"),
        (3, False, "is excellent answerer or not"),
    ],
    "info_topic.csv": [
        (0, False, "topic ID"),
    ],
    "info_token.csv": [
        (0, False, "token ID"),
        (1, False, "word2vec vector with 64 dimensions (space separated)"),
    ],
}


JOIN_SUMMARY = [
    "inter_impression.user_id -> info_user.user_id",
    "inter_impression.answer_id -> info_answer.answer_id",
    "inter_query.user_id -> info_user.user_id",
    "inter_query.token_ids -> info_token.token_id",
    "info_answer.question_id -> info_question.question_id",
    "info_answer.author_id -> info_author.author_id",
    "info_answer.topic_ids -> info_topic.topic_id",
    "info_answer.token_ids -> info_token.token_id",
    "info_question.topic_ids -> info_topic.topic_id",
    "info_question.token_ids -> info_token.token_id",
    "info_user.followed_topic_ids -> info_topic.topic_id",
]


def configure_csv_field_limit() -> None:
    """Raise the CSV parser field limit for long token-vector rows."""
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            return
        except OverflowError:
            limit //= 10


PK_TABLES = {
    "info_user.csv": "user ID",
    "info_answer.csv": "answer ID",
    "info_question.csv": "question ID",
    "info_author.csv": "author ID",
    "info_topic.csv": "topic ID",
    "info_token.csv": "token ID",
}


@dataclass
class PkReport:
    table: str
    key_name: str
    rows: int
    unique_keys: int

    @property
    def duplicate_rows(self) -> int:
        return self.rows - self.unique_keys


@dataclass
class FkReport:
    label: str
    checked: int
    matched: int
    missing: int
    example_missing: List[str]


def default_data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "zhihurec_1m" / "raw"


def iter_rows(path: Path) -> Iterable[List[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            yield row


def load_pk_set(path: Path, key_name: str) -> Tuple[Set[str], PkReport]:
    keys: Set[str] = set()
    rows = 0
    for row in iter_rows(path):
        if not row:
            continue
        rows += 1
        keys.add(row[0])
    return keys, PkReport(
        table=path.name,
        key_name=key_name,
        rows=rows,
        unique_keys=len(keys),
    )


def format_nullable(nullable: bool) -> str:
    return "nullable" if nullable else "not-null in README"


def print_field_docs() -> None:
    print("== Field Meanings From README ==")
    for table in TABLE_ORDER:
        print(f"\n[{table}]")
        for index, nullable, description in FIELD_DOCS[table]:
            print(f"  {index:>2} | {format_nullable(nullable):<18} | {description}")


def check_scalar_fk(
    path: Path,
    column_index: int,
    target_keys: Set[str],
    label: str,
    row_limit: int,
    allow_empty: bool = False,
) -> FkReport:
    checked = 0
    matched = 0
    missing = 0
    examples: List[str] = []

    for row_no, row in enumerate(iter_rows(path), start=1):
        if row_no > row_limit:
            break
        if column_index >= len(row):
            continue
        value = row[column_index].strip()
        if not value and allow_empty:
            continue
        if not value:
            missing += 1
            if len(examples) < 5:
                examples.append("<empty>")
            continue
        checked += 1
        if value in target_keys:
            matched += 1
        else:
            missing += 1
            if len(examples) < 5:
                examples.append(value)

    return FkReport(
        label=label,
        checked=checked,
        matched=matched,
        missing=missing,
        example_missing=examples,
    )


def check_space_separated_fk(
    path: Path,
    column_index: int,
    target_keys: Set[str],
    label: str,
    row_limit: int,
    max_ref_checks: int,
    allow_empty: bool = True,
) -> FkReport:
    checked = 0
    matched = 0
    missing = 0
    examples: List[str] = []

    for row_no, row in enumerate(iter_rows(path), start=1):
        if row_no > row_limit or checked >= max_ref_checks:
            break
        if column_index >= len(row):
            continue
        value = row[column_index].strip()
        if not value and allow_empty:
            continue
        if not value:
            missing += 1
            if len(examples) < 5:
                examples.append("<empty>")
            continue

        for token in value.split():
            if checked >= max_ref_checks:
                break
            checked += 1
            if token in target_keys:
                matched += 1
            else:
                missing += 1
                if len(examples) < 5:
                    examples.append(token)

    return FkReport(
        label=label,
        checked=checked,
        matched=matched,
        missing=missing,
        example_missing=examples,
    )


def print_pk_reports(pk_reports: Sequence[PkReport]) -> None:
    print("\n== Primary Key Checks ==")
    for report in pk_reports:
        print(
            f"{report.table}: rows={report.rows}, unique_{report.key_name}={report.unique_keys}, "
            f"duplicate_rows={report.duplicate_rows}"
        )


def print_fk_reports(fk_reports: Sequence[FkReport]) -> None:
    print("\n== Sample Foreign-Key Checks ==")
    for report in fk_reports:
        sample = ", ".join(report.example_missing) if report.example_missing else "-"
        print(
            f"{report.label}: checked={report.checked}, matched={report.matched}, "
            f"missing={report.missing}, missing_examples={sample}"
        )


def print_join_summary() -> None:
    print("\n== Join Summary ==")
    for line in JOIN_SUMMARY:
        print(f"- {line}")


def ensure_files_exist(data_dir: Path) -> None:
    missing = [name for name in TABLE_ORDER if not (data_dir / name).exists()]
    if missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(f"Missing expected files under {data_dir}: {joined}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect ZhihuRec-1M tables and key relationships.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=default_data_dir(),
        help="Directory that contains the eight ZhihuRec CSV files.",
    )
    parser.add_argument(
        "--row-sample",
        type=int,
        default=5000,
        help="How many rows to scan per table for scalar foreign-key checks.",
    )
    parser.add_argument(
        "--max-ref-checks",
        type=int,
        default=20000,
        help="Upper bound for sampled space-separated reference IDs per relation.",
    )
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    configure_csv_field_limit()
    ensure_files_exist(data_dir)

    print(f"Inspecting ZhihuRec tables under: {data_dir}")
    print_field_docs()

    pk_sets: Dict[str, Set[str]] = {}
    pk_reports: List[PkReport] = []
    for table, key_name in PK_TABLES.items():
        key_set, report = load_pk_set(data_dir / table, key_name)
        pk_sets[table] = key_set
        pk_reports.append(report)

    print_pk_reports(pk_reports)

    fk_reports = [
        check_scalar_fk(
            data_dir / "inter_impression.csv",
            0,
            pk_sets["info_user.csv"],
            "inter_impression.user_id -> info_user.user_id",
            args.row_sample,
        ),
        check_scalar_fk(
            data_dir / "inter_impression.csv",
            1,
            pk_sets["info_answer.csv"],
            "inter_impression.answer_id -> info_answer.answer_id",
            args.row_sample,
        ),
        check_scalar_fk(
            data_dir / "inter_query.csv",
            0,
            pk_sets["info_user.csv"],
            "inter_query.user_id -> info_user.user_id",
            args.row_sample,
        ),
        check_space_separated_fk(
            data_dir / "inter_query.csv",
            1,
            pk_sets["info_token.csv"],
            "inter_query.token_ids -> info_token.token_id",
            args.row_sample,
            args.max_ref_checks,
        ),
        check_scalar_fk(
            data_dir / "info_answer.csv",
            1,
            pk_sets["info_question.csv"],
            "info_answer.question_id -> info_question.question_id",
            args.row_sample,
            allow_empty=True,
        ),
        check_scalar_fk(
            data_dir / "info_answer.csv",
            3,
            pk_sets["info_author.csv"],
            "info_answer.author_id -> info_author.author_id",
            args.row_sample,
            allow_empty=True,
        ),
        check_space_separated_fk(
            data_dir / "info_answer.csv",
            16,
            pk_sets["info_token.csv"],
            "info_answer.token_ids -> info_token.token_id",
            args.row_sample,
            args.max_ref_checks,
        ),
        check_space_separated_fk(
            data_dir / "info_answer.csv",
            17,
            pk_sets["info_topic.csv"],
            "info_answer.topic_ids -> info_topic.topic_id",
            args.row_sample,
            args.max_ref_checks,
        ),
        check_space_separated_fk(
            data_dir / "info_question.csv",
            6,
            pk_sets["info_token.csv"],
            "info_question.token_ids -> info_token.token_id",
            args.row_sample,
            args.max_ref_checks,
        ),
        check_space_separated_fk(
            data_dir / "info_question.csv",
            7,
            pk_sets["info_topic.csv"],
            "info_question.topic_ids -> info_topic.topic_id",
            args.row_sample,
            args.max_ref_checks,
        ),
        check_space_separated_fk(
            data_dir / "info_user.csv",
            26,
            pk_sets["info_topic.csv"],
            "info_user.followed_topic_ids -> info_topic.topic_id",
            args.row_sample,
            args.max_ref_checks,
        ),
    ]

    print_fk_reports(fk_reports)
    print_join_summary()


if __name__ == "__main__":
    main()
