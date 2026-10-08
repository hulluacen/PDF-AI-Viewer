"""Persistent data paths. Bundled resources and working directory are unrelated."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


def application_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def legacy_dir() -> Path:
    return Path.home() / ".pdftranslator"


def atomic_json(path: Path, value) -> None:
    """Replace only after a complete write; failures preserve the previous file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _copy_missing(source: Path, destination: Path) -> None:
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".migrate-", dir=destination.parent)
    os.close(fd)
    try:
        shutil.copyfile(source, temporary)
        # Migration is single-threaded at startup. Never replace existing data.
        if not destination.exists():
            os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def initialize_data(root: Path | None = None, old: Path | None = None) -> Path:
    root = Path(root) if root is not None else application_dir() / "data"
    old = Path(old) if old is not None else legacy_dir()
    root.mkdir(parents=True, exist_ok=True)
    # Fail visibly if a portable folder is read-only; never silently change location.
    fd, probe = tempfile.mkstemp(prefix=".probe-", dir=root)
    os.close(fd)
    os.unlink(probe)
    marker = root / "migration-v1.json"
    if not marker.exists():
        for name in ("settings.json", "reading_positions.json", "recent.json"):
            if (old / name).is_file():
                _copy_missing(old / name, root / name)
        if (old / "chatnotes").is_dir():
            for source in (old / "chatnotes").glob("*.md"):
                _copy_missing(source, root / "chatnotes" / source.name)
        atomic_json(marker, {"schema": 1, "source": str(old), "originals_preserved": True})
    return root


_data_root = None


def data_dir() -> Path:
    global _data_root
    if _data_root is None:
        _data_root = initialize_data()
    return _data_root
