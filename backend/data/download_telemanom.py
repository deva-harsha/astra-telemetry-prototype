import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path


DATA_URLS = (
    "https://s3-us-west-2.amazonaws.com/telemanom/data.zip",
    "https://www.kaggle.com/api/v1/datasets/download/patrickfleith/nasa-anomaly-detection-dataset-smap-msl",
)
LABELS_URL = "https://raw.githubusercontent.com/khundman/telemanom/master/labeled_anomalies.csv"
DEFAULT_DESTINATION = Path("data/external/telemanom")


def _download(url: str, destination: Path) -> str:
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
    return digest.hexdigest()




def _download_first(urls: tuple[str, ...], destination: Path) -> tuple[str, str]:
    failures: list[str] = []
    for url in urls:
        try:
            return url, _download(url, destination)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            destination.unlink(missing_ok=True)
            failures.append(f"{url}: {exc}")
    raise RuntimeError("All documented Telemanom download sources failed:" + chr(10) + chr(10).join(failures))

def _safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if root != target and root not in target.parents:
            raise ValueError(f"Unsafe archive member: {member.filename}")
    archive.extractall(destination)


def download(destination: Path = DEFAULT_DESTINATION, force: bool = False) -> Path:
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        if not force:
            raise FileExistsError(f"{destination} is not empty; use --force to replace downloaded data")
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        archive_path = Path(temporary) / "data.zip"
        data_url, archive_sha = _download_first(DATA_URLS, archive_path)
        with zipfile.ZipFile(archive_path) as archive:
            _safe_extract(archive, destination)

    labels_path = destination / "labeled_anomalies.csv"
    labels_sha = _download(LABELS_URL, labels_path)
    has_train = any(path.is_dir() for path in destination.rglob("train"))
    has_test = any(path.is_dir() for path in destination.rglob("test"))
    if not has_train or not has_test:
        if force:
            shutil.rmtree(destination)
        raise ValueError("Official archive did not contain expected train/ and test/ directories")

    metadata = {
        "source_repository": "https://github.com/khundman/telemanom",
        "data_url": data_url,
        "documented_data_urls": list(DATA_URLS),
        "labels_url": LABELS_URL,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_archive_sha256": archive_sha,
        "labels_sha256": labels_sha,
    }
    (destination / "provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Download official Telemanom SMAP/MSL data")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(download(args.destination, args.force))


if __name__ == "__main__":
    main()



