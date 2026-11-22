"""Atomic, versioned scrcpy runtime management with staging, multi-version retention, and rollback."""
import json
import os
from pathlib import Path
import shutil
import uuid
import zipfile

from updater import get_installed_scrcpy_version, parse_version


def get_active_pointer(runtime_root: Path) -> dict | None:
    """Read and validate the active runtime pointer file."""
    pointer_path = Path(runtime_root) / "active.json"
    if not pointer_path.is_file():
        return None

    try:
        data = json.loads(pointer_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None

        rel_path_str = data.get("relative_path")
        if not rel_path_str:
            return None

        # Ensure relative path does not escape versions directory
        rel_path = Path(rel_path_str)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            return None

        target_dir = (Path(runtime_root) / rel_path).resolve()
        versions_root = (Path(runtime_root) / "versions").resolve()
        try:
            target_dir.relative_to(versions_root)
        except ValueError:
            return None

        # Validate target directory contains required binaries
        if is_valid_runtime_dir(target_dir):
            return data

        # If active target is missing/corrupted, check if previous runtime can be recovered
        prev_rel_str = data.get("previous_relative_path")
        if prev_rel_str:
            prev_rel = Path(prev_rel_str)
            if not prev_rel.is_absolute() and ".." not in prev_rel.parts:
                prev_target = (Path(runtime_root) / prev_rel).resolve()
                try:
                    prev_target.relative_to(versions_root)
                    if is_valid_runtime_dir(prev_target):
                        # Recover pointer to previous
                        recovered_data = {
                            "version": prev_target.name,
                            "relative_path": prev_rel_str,
                            "previous_relative_path": None,
                        }
                        write_active_pointer(
                            runtime_root,
                            recovered_data["version"],
                            recovered_data["relative_path"],
                            None,
                        )
                        return recovered_data
                except ValueError:
                    pass

        return None
    except Exception:
        return None


def get_active_runtime_dir(runtime_root: Path = None) -> Path | None:
    """Return the absolute path to the active versioned runtime directory, or None."""
    if runtime_root is None:
        from assets import get_writable_runtime
        runtime_root = get_writable_runtime()

    pointer = get_active_pointer(runtime_root)
    if pointer and pointer.get("relative_path"):
        target = (Path(runtime_root) / pointer["relative_path"]).resolve()
        if is_valid_runtime_dir(target):
            return target
    return None


def write_active_pointer(
    runtime_root: Path,
    version: str,
    relative_path: str,
    previous_relative_path: str = None,
) -> bool:
    """Atomically update active.json using a temporary file and replace."""
    root = Path(runtime_root)
    root.mkdir(parents=True, exist_ok=True)
    data = {
        "version": str(version),
        "relative_path": str(relative_path).replace("\\", "/"),
        "previous_relative_path": (
            str(previous_relative_path).replace("\\", "/")
            if previous_relative_path
            else None
        ),
    }
    content = json.dumps(data, indent=2)
    tmp_path = root / f".active_{os.getpid()}_{uuid.uuid4().hex}.tmp"
    target_path = root / "active.json"
    try:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, target_path)
        return True
    except Exception as exc:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise exc


def remove_active_pointer(runtime_root: Path = None) -> bool:
    """Remove active.json safely if it exists (used for first-activation rollback)."""
    if runtime_root is None:
        from assets import get_writable_runtime
        runtime_root = get_writable_runtime()
    target = Path(runtime_root) / "active.json"
    if target.exists():
        try:
            target.unlink()
            return True
        except OSError:
            pass
    return False


def is_valid_runtime_dir(directory: Path) -> bool:
    """Check if directory contains all required scrcpy distribution binaries."""
    d = Path(directory)
    if not d.is_dir():
        return False
    required = ("scrcpy.exe", "adb.exe", "scrcpy-server")
    return all((d / name).is_file() for name in required)


def safe_extract_scrcpy_zip(zip_path: Path, dest_dir: Path) -> Path:
    """Safely extract scrcpy archive into dest_dir, preventing path traversal and collisions.

    Recognizes the official scrcpy distribution root directory and preserves relative paths
    below it.
    """
    dest = Path(dest_dir).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    if not zipfile.is_zipfile(zip_path):
        raise ValueError("Invalid or corrupted zip archive.")

    with zipfile.ZipFile(zip_path) as zf:
        infolist = zf.infolist()
        if not infolist:
            raise ValueError("Empty zip archive.")

        # Determine if all non-empty entries share a single common top-level directory
        non_empty = [info for info in infolist if info.filename.strip("/\\")]
        first_components = set()
        for info in non_empty:
            parts = Path(info.filename).parts
            if parts:
                first_components.add(parts[0])

        strip_prefix = None
        if len(first_components) == 1:
            candidate_prefix = list(first_components)[0]
            if any(len(Path(info.filename).parts) > 1 for info in non_empty):
                strip_prefix = candidate_prefix

        seen_targets = set()

        for info in infolist:
            # Check for symlinks
            is_symlink = (info.external_attr >> 16) & 0o170000 == 0o120000
            if is_symlink:
                raise ValueError(f"Symlinks are not allowed in archive: {info.filename}")

            parts = list(Path(info.filename).parts)
            if not parts:
                continue

            if ".." in parts or Path(info.filename).is_absolute():
                raise ValueError(f"Path traversal detected in archive entry: {info.filename}")

            if strip_prefix and parts[0] == strip_prefix:
                parts = parts[1:]

            if not parts:
                continue

            rel_target = Path(*parts)
            target_file = (dest / rel_target).resolve()

            # Verify destination is strictly within dest_dir
            try:
                target_file.relative_to(dest)
            except ValueError:
                raise ValueError(f"Archive entry escapes destination: {info.filename}")

            if info.is_dir():
                target_file.mkdir(parents=True, exist_ok=True)
                continue

            norm_key = str(rel_target).lower()
            if norm_key in seen_targets:
                raise ValueError(f"Duplicate or colliding destination path in archive: {rel_target}")
            seen_targets.add(norm_key)

            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_bytes(zf.read(info))

    return dest


def validate_runtime_dir(runtime_dir: Path, expected_version: str = None) -> str:
    """Validate extracted runtime directory contents and executable operability."""
    d = Path(runtime_dir).resolve()
    if not is_valid_runtime_dir(d):
        missing = [name for name in ("scrcpy.exe", "adb.exe", "scrcpy-server") if not (d / name).is_file()]
        raise ValueError(f"Runtime missing required files: {', '.join(missing)}")

    scrcpy_exe = d / "scrcpy.exe"
    detected_ver = get_installed_scrcpy_version(scrcpy_exe)

    if detected_ver and expected_version:
        detected_tuple = parse_version(detected_ver)
        expected_tuple = parse_version(expected_version)
        if detected_tuple and expected_tuple and detected_tuple != expected_tuple:
            raise ValueError(
                f"Extracted executable version '{detected_ver}' does not match expected version '{expected_version}'"
            )

    return detected_ver or expected_version or "5.0.1"


def stage_and_validate_runtime(
    zip_path: Path,
    runtime_root: Path = None,
    expected_version: str = None,
) -> tuple[Path, str]:
    """Extract zip into a unique staging directory and validate contents."""
    if runtime_root is None:
        from assets import get_writable_runtime
        runtime_root = get_writable_runtime()

    staging_parent = Path(runtime_root) / "staging"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging_dir = staging_parent / f"stage_{os.getpid()}_{uuid.uuid4().hex}"

    try:
        safe_extract_scrcpy_zip(zip_path, staging_dir)
        version = validate_runtime_dir(staging_dir, expected_version)
        return staging_dir, version
    except Exception as exc:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise exc


def promote_staging_to_version(
    staging_dir: Path,
    version: str,
    runtime_root: Path = None,
) -> Path:
    """Move a validated staging directory into the inactive versions directory."""
    if runtime_root is None:
        from assets import get_writable_runtime
        runtime_root = get_writable_runtime()

    versions_root = Path(runtime_root) / "versions"
    versions_root.mkdir(parents=True, exist_ok=True)
    target_dir = versions_root / version

    # Avoid modifying a version directory already in active use
    active_dir = get_active_runtime_dir(runtime_root)
    if active_dir and active_dir.resolve() == target_dir.resolve():
        raise RuntimeError(f"Version {version} is currently active and cannot be modified.")

    # If an older inactive copy of this version exists, replace it safely
    if target_dir.exists():
        trash_dir = versions_root / f".trash_{uuid.uuid4().hex}"
        try:
            target_dir.rename(trash_dir)
            shutil.rmtree(trash_dir, ignore_errors=True)
        except OSError:
            # If rename failed, try direct rmtree
            shutil.rmtree(target_dir, ignore_errors=True)

    staging_dir.rename(target_dir)
    return target_dir


def get_installed_runtimes(runtime_root: Path = None) -> list[str]:
    """Scan versions/ directory and return list of valid installed version strings, newest first."""
    if runtime_root is None:
        from assets import get_writable_runtime
        runtime_root = get_writable_runtime()
    versions_root = Path(runtime_root) / "versions"
    if not versions_root.is_dir():
        return []

    installed = []
    for item in versions_root.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            if is_valid_runtime_dir(item):
                installed.append(item.name)

    installed.sort(key=lambda v: parse_version(v) or (0, 0, 0), reverse=True)
    return installed


def get_installed_runtime_path(version: str, runtime_root: Path = None) -> Path | None:
    """Return path to installed version directory if it exists and is valid."""
    if runtime_root is None:
        from assets import get_writable_runtime
        runtime_root = get_writable_runtime()
    target = Path(runtime_root) / "versions" / version
    if target.is_dir() and is_valid_runtime_dir(target):
        return target
    return None


def clean_unused_runtimes(runtime_root: Path = None, keep_versions: set = None) -> list[str]:
    """Explicitly clean up unneeded locally installed versions while retaining active and previous runtimes.

    Returns list of removed version names.
    """
    if runtime_root is None:
        from assets import get_writable_runtime
        runtime_root = get_writable_runtime()

    versions_root = Path(runtime_root) / "versions"
    if not versions_root.is_dir():
        return []

    keep = set(keep_versions or ())
    pointer = get_active_pointer(runtime_root)
    if pointer:
        if pointer.get("version"):
            keep.add(str(pointer["version"]))
        if pointer.get("relative_path"):
            keep.add(Path(pointer["relative_path"]).name)
        if pointer.get("previous_relative_path"):
            keep.add(Path(pointer["previous_relative_path"]).name)

    removed = []
    for item in versions_root.iterdir():
        if item.is_dir() and item.name not in keep and not item.name.startswith("."):
            try:
                shutil.rmtree(item, ignore_errors=True)
                removed.append(item.name)
            except OSError:
                pass
    return removed


def prune_old_versions(runtime_root: Path = None, keep_versions: set = None):
    """Retention policy: keep current active version, previous known-good version,
    and any explicitly retained versions in keep_versions.
    """
    if runtime_root is None:
        from assets import get_writable_runtime
        runtime_root = get_writable_runtime()

    versions_root = Path(runtime_root) / "versions"
    if not versions_root.is_dir():
        return

    keep = set(keep_versions or ())
    pointer = get_active_pointer(runtime_root)
    if pointer:
        if pointer.get("version"):
            keep.add(str(pointer["version"]))
        if pointer.get("relative_path"):
            keep.add(Path(pointer["relative_path"]).name)
        if pointer.get("previous_relative_path"):
            keep.add(Path(pointer["previous_relative_path"]).name)

    for item in versions_root.iterdir():
        if item.is_dir() and item.name.startswith(".trash"):
            try:
                shutil.rmtree(item, ignore_errors=True)
            except OSError:
                pass
        elif item.is_dir() and item.name not in keep and not item.name.startswith("."):
            try:
                shutil.rmtree(item, ignore_errors=True)
            except OSError:
                pass


def cleanup_staging(runtime_root: Path = None):
    """Clean up incomplete temporary directories from previous runs."""
    if runtime_root is None:
        from assets import get_writable_runtime
        runtime_root = get_writable_runtime()

    staging_parent = Path(runtime_root) / "staging"
    if staging_parent.is_dir():
        for item in staging_parent.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
            except OSError:
                pass
