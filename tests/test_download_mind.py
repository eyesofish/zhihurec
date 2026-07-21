from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from urllib.request import Request

import pytest

from scripts.download_mind import MindDownloadError, download_dataset


class FakeResponse(io.BytesIO):
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def _archive_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "news.tsv", "N1\tnews\tlocal\tTitle\tAbstract\thttps://example.com\t[]\t[]\n"
        )
        archive.writestr(
            "behaviors.tsv",
            "1\tU1\t11/13/2019 8:36:57 AM\t\tN1-1\n",
        )
    return buffer.getvalue()


def test_download_requires_explicit_license_acceptance(tmp_path: Path):
    with pytest.raises(MindDownloadError, match="accept-license"):
        download_dataset(
            variant="small",
            splits=("train",),
            raw_root=tmp_path / "raw",
            meta_root=tmp_path / "meta",
            accept_license=False,
        )


def test_download_extracts_and_reuses_checksum_verified_archive(tmp_path: Path):
    payload = _archive_bytes()
    requests: list[Request] = []

    def opener(request: Request) -> FakeResponse:
        requests.append(request)
        return FakeResponse(payload)

    kwargs = {
        "variant": "small",
        "splits": ("train",),
        "raw_root": tmp_path / "raw",
        "meta_root": tmp_path / "meta",
        "accept_license": True,
        "opener": opener,
    }
    first = download_dataset(**kwargs)
    second = download_dataset(**kwargs)

    assert first[0].downloaded is True
    assert second[0].downloaded is False
    assert len(requests) == 1
    assert (tmp_path / "raw/small/train/news.tsv").is_file()
    manifest = json.loads((tmp_path / "meta/download_manifest.json").read_text())
    assert manifest["license_accepted_by_cli_flag"] is True
    assert manifest["official_download_page"].startswith("https://msnews.github.io/")
    checksums = json.loads((tmp_path / "meta/local_checksums.json").read_text())
    assert checksums["algorithm"] == "sha256"
