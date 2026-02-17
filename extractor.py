"""
Archive detection and extraction logic (no UI dependencies).
"""
import os
import time
from typing import Callable, Optional

import rarfile
import zipfile

SUPPORTED_EXTENSIONS = (".rar", ".zip")


def wait_for_new_file(download_folder: str, poll_interval: float = 0.5) -> None:
    """Block until at least one new file appears in download_folder."""
    initial = set(os.listdir(download_folder))
    while True:
        current = set(os.listdir(download_folder))
        if current != initial:
            return
        time.sleep(poll_interval)


def wait_for_download_complete(
    download_folder: str,
    poll_interval: float = 0.5,
) -> set:
    """
    Block until no filename in the folder contains 'cr' (e.g. .crdownload temp files).
    Returns the current set of filenames in the folder.
    """
    current = set(os.listdir(download_folder))
    while any("cr" in name for name in current):
        time.sleep(poll_interval)
        current = set(os.listdir(download_folder))
    return current


def get_new_archive_path(
    download_folder: str, initial_files: set, current_files: set
) -> Optional[str]:
    """Return the path to the first new RAR or ZIP, or None."""
    new_names = [
        n for n in (current_files - initial_files)
        if n.lower().endswith((".rar", ".zip"))
    ]
    if not new_names:
        return None
    return os.path.normpath(os.path.join(download_folder, new_names[0]))


def open_archive(archive_path: str):
    """
    Open a RAR or ZIP file. Returns an archive-like object with .namelist() and .extract(member, path=).
    """
    path_lower = archive_path.lower()
    if path_lower.endswith(".rar"):
        return rarfile.RarFile(archive_path)
    if path_lower.endswith(".zip"):
        return zipfile.ZipFile(archive_path, "r")
    raise ValueError(f"Unsupported archive format: {archive_path}")


def extract_archive(
    archive_path: str,
    extract_folder: str,
    on_status: Optional[Callable[[str], None]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> None:
    """
    Extract a RAR or ZIP to extract_folder. Callbacks:
    - on_status(message) for current file being extracted
    - on_progress(current, total) for progress (total can be 100 for percentage).
    """
    archive = open_archive(archive_path)
    base_name = os.path.splitext(os.path.basename(archive_path))[0]
    dest_dir = os.path.normpath(os.path.join(extract_folder, base_name))

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    names = archive.namelist()
    total = len(names)
    if on_progress:
        on_progress(0, 100)

    for i, name in enumerate(names):
        if on_status:
            on_status(f"Extracting {name}")
        archive.extract(name, path=dest_dir)
        if on_progress and total > 0:
            value = int(100 * (i + 1) / total)
            on_progress(value, 100)

    archive.close()
