from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LICENSE_URL = "https://github.com/msnews/MIND/blob/master/MSR%20License_Data.pdf"
OFFICIAL_DOWNLOAD_PAGE = "https://msnews.github.io/#getting-start"
OFFICIAL_DOWNLOADS = {
    variant: {
        split: (
            f"https://huggingface.co/datasets/yjw1029/MIND/resolve/main/MIND{variant}_{split}.zip"
        )
        for split in ("train", "dev")
    }
    for variant in ("small", "large")
}
REQUIRED_ARCHIVE_FILES = {"behaviors.tsv", "news.tsv"}
HUYVA_MIRROR_REPOSITORY = "https://huggingface.co/datasets/huyva/MIND-small"
HUYVA_MIRROR_DOWNLOADS = {
    split: {
        filename: f"{HUYVA_MIRROR_REPOSITORY}/resolve/main/{split}/{filename}"
        for filename in REQUIRED_ARCHIVE_FILES
    }
    for split in ("train", "dev")
}


class MindDownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class DownloadRecord:
    variant: str
    split: str
    source: str
    source_kind: str
    url: str
    local_path: str
    extracted_path: str | None
    sha256: str
    size_bytes: int
    downloaded: bool


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MindDownloadError(f"Cannot read JSON manifest {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MindDownloadError(f"Expected JSON object in {path}")
    return value


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(payload)
        temporary_path = Path(handle.name)
    temporary_path.replace(path)


def _authorization_headers(token: str | None) -> dict[str, str]:
    resolved_token = token or os.environ.get("HF_TOKEN")
    return {"Authorization": f"Bearer {resolved_token}"} if resolved_token else {}


def _default_opener(request: Request) -> BinaryIO:
    return urlopen(request, timeout=120)


def _download_file(
    url: str,
    destination: Path,
    *,
    token: str | None,
    opener: Callable[[Request], BinaryIO] = _default_opener,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(
        url,
        headers={
            "User-Agent": "NewsIntentRec-MIND-downloader/1.0",
            **_authorization_headers(token),
        },
    )
    temporary_path = destination.with_suffix(f"{destination.suffix}.part")
    temporary_path.unlink(missing_ok=True)
    try:
        with opener(request) as response, temporary_path.open("wb") as output:
            shutil.copyfileobj(response, output)
        if temporary_path.stat().st_size == 0:
            raise MindDownloadError(f"Downloaded empty archive from {url}")
        temporary_path.replace(destination)
    except HTTPError as exc:
        temporary_path.unlink(missing_ok=True)
        if exc.code in {401, 403}:
            raise MindDownloadError(
                "MIND download access was denied. Accept the gated dataset terms at "
                "https://huggingface.co/datasets/yjw1029/MIND, create a read token, "
                "and set HF_TOKEN before retrying."
            ) from exc
        raise MindDownloadError(f"Download failed with HTTP {exc.code}: {url}") from exc
    except (OSError, URLError) as exc:
        temporary_path.unlink(missing_ok=True)
        raise MindDownloadError(f"Download failed for {url}: {exc}") from exc


def _safe_members(archive: zipfile.ZipFile, destination: Path) -> Iterable[zipfile.ZipInfo]:
    root = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if target != root and root not in target.parents:
            raise MindDownloadError(f"Unsafe archive member: {member.filename}")
        yield member


def extract_archive(archive_path: Path, destination: Path) -> None:
    with tempfile.TemporaryDirectory(
        prefix=f".{destination.name}.",
        dir=destination.parent,
    ) as temporary_directory:
        temporary_path = Path(temporary_directory)
        try:
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(temporary_path, members=_safe_members(archive, temporary_path))
        except (OSError, zipfile.BadZipFile) as exc:
            raise MindDownloadError(f"Invalid MIND archive {archive_path}: {exc}") from exc

        extracted_names = {path.name for path in temporary_path.iterdir() if path.is_file()}
        missing = REQUIRED_ARCHIVE_FILES - extracted_names
        if missing:
            raise MindDownloadError(
                f"Archive {archive_path} is missing required files: {sorted(missing)}"
            )

        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(temporary_path, destination)


def _checksum_entries(checksum_manifest: dict[str, object]) -> dict[str, str]:
    files = checksum_manifest.get("files", {})
    if not isinstance(files, dict):
        return {}
    return {
        str(path): str(digest)
        for path, digest in files.items()
        if isinstance(path, str) and isinstance(digest, str)
    }


def download_dataset(
    *,
    variant: str,
    splits: Iterable[str],
    raw_root: Path,
    meta_root: Path,
    accept_license: bool,
    source: str = "official",
    token: str | None = None,
    opener: Callable[[Request], BinaryIO] = _default_opener,
) -> list[DownloadRecord]:
    if not accept_license:
        raise MindDownloadError(
            f"Pass --accept-license after reading the Microsoft Research License: {LICENSE_URL}"
        )
    if variant not in OFFICIAL_DOWNLOADS:
        raise MindDownloadError(f"Unsupported MIND variant: {variant}")
    if source not in {"official", "huyva"}:
        raise MindDownloadError(f"Unsupported MIND source: {source}")
    if source == "huyva" and variant != "small":
        raise MindDownloadError("The huyva mirror only provides MIND-small")

    selected_splits = tuple(splits)
    invalid_splits = set(selected_splits) - {"train", "dev"}
    if invalid_splits:
        raise MindDownloadError(f"Unsupported MIND splits: {sorted(invalid_splits)}")

    checksum_path = meta_root / "local_checksums.json"
    previous_checksums = _checksum_entries(_load_json(checksum_path))
    records: list[DownloadRecord] = []
    checksum_entries = dict(previous_checksums)

    for split in selected_splits:
        if source == "huyva":
            for filename in sorted(REQUIRED_ARCHIVE_FILES):
                file_path = raw_root / variant / split / filename
                relative_path = file_path.relative_to(raw_root.parent).as_posix()
                expected_digest = previous_checksums.get(relative_path)
                downloaded = True
                if file_path.exists() and expected_digest:
                    actual_digest = sha256_file(file_path)
                    if actual_digest == expected_digest:
                        downloaded = False
                    else:
                        file_path.unlink()
                if downloaded:
                    _download_file(
                        HUYVA_MIRROR_DOWNLOADS[split][filename],
                        file_path,
                        token=token,
                        opener=opener,
                    )
                digest = sha256_file(file_path)
                checksum_entries[relative_path] = digest
                records.append(
                    DownloadRecord(
                        variant=variant,
                        split=split,
                        source="huyva/MIND-small",
                        source_kind="third_party_mirror",
                        url=HUYVA_MIRROR_DOWNLOADS[split][filename],
                        local_path=relative_path,
                        extracted_path=None,
                        sha256=digest,
                        size_bytes=file_path.stat().st_size,
                        downloaded=downloaded,
                    )
                )
            continue

        archive_name = f"MIND{variant}_{split}.zip"
        archive_path = raw_root / variant / "_archives" / archive_name
        extracted_path = raw_root / variant / split
        relative_archive = archive_path.relative_to(raw_root.parent).as_posix()
        expected_digest = previous_checksums.get(relative_archive)
        downloaded = True

        if archive_path.exists() and expected_digest:
            actual_digest = sha256_file(archive_path)
            if actual_digest == expected_digest:
                downloaded = False
            else:
                archive_path.unlink()

        if downloaded:
            _download_file(
                OFFICIAL_DOWNLOADS[variant][split],
                archive_path,
                token=token,
                opener=opener,
            )

        digest = sha256_file(archive_path)
        checksum_entries[relative_archive] = digest
        if downloaded or not all(
            (extracted_path / name).exists() for name in REQUIRED_ARCHIVE_FILES
        ):
            extracted_path.parent.mkdir(parents=True, exist_ok=True)
            extract_archive(archive_path, extracted_path)

        records.append(
            DownloadRecord(
                variant=variant,
                split=split,
                source="official_mind_download_page",
                source_kind="official",
                url=OFFICIAL_DOWNLOADS[variant][split],
                local_path=relative_archive,
                extracted_path=extracted_path.relative_to(raw_root.parent).as_posix(),
                sha256=digest,
                size_bytes=archive_path.stat().st_size,
                downloaded=downloaded,
            )
        )

    generated_at = datetime.now(UTC).isoformat()
    _write_json(
        checksum_path,
        {
            "generated_at": generated_at,
            "algorithm": "sha256",
            "files": checksum_entries,
        },
    )
    _write_json(
        meta_root / "download_manifest.json",
        {
            "generated_at": generated_at,
            "license_url": LICENSE_URL,
            "official_download_page": OFFICIAL_DOWNLOAD_PAGE,
            "selected_source": source,
            "third_party_mirror_repository": (
                HUYVA_MIRROR_REPOSITORY if source == "huyva" else None
            ),
            "license_accepted_by_cli_flag": True,
            "files": [asdict(record) for record in records],
        },
    )
    return records


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download the public Microsoft MIND dataset.")
    parser.add_argument("--variant", choices=("small", "large"), default="small")
    parser.add_argument("--split", choices=("train", "dev", "all"), default="all")
    parser.add_argument("--source", choices=("official", "huyva"), default="official")
    parser.add_argument("--accept-license", action="store_true")
    parser.add_argument("--raw-root", type=Path, default=Path("data/mind/raw"))
    parser.add_argument("--meta-root", type=Path, default=Path("data/mind/meta"))
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    splits = ("train", "dev") if args.split == "all" else (args.split,)
    try:
        records = download_dataset(
            variant=args.variant,
            splits=splits,
            raw_root=args.raw_root,
            meta_root=args.meta_root,
            accept_license=args.accept_license,
            source=args.source,
        )
    except MindDownloadError as exc:
        print(f"error: {exc}")
        return 1

    for record in records:
        action = "downloaded" if record.downloaded else "verified cached"
        print(
            f"{action}: {record.variant}/{record.split} {record.local_path} sha256={record.sha256}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
