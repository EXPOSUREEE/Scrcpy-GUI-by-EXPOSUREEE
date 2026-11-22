"""GitHub release discovery, semantic version parsing, and caching for Scrcpy Deck and scrcpy."""
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
import urllib.error
import urllib.request

DECK_REPO = "EXPOSUREEE/Scrcpy-GUI-by-EXPOSUREEE"
SCRCPY_REPO = "Genymobile/scrcpy"
CACHE_TTL_SECONDS = 3600  # 1 hour cache validity
CACHE_FILE: Path | None = None


def parse_semver(text: str) -> tuple[int, int, int] | None:
    """Parse text into (major, minor, patch) integer tuple.

    Handles '5.0.1', 'v5.0.1', '5.0', 'v4.1', 'v3.3.4', 'ScrcpyDeck 4.0.2', etc.
    """
    if not text:
        return None
    match = re.search(r"\bv?(\d+)\.(\d+)(?:\.(\d+))?\b", str(text), re.IGNORECASE)
    if match:
        patch = int(match.group(3)) if match.group(3) is not None else 0
        return (int(match.group(1)), int(match.group(2)), patch)
    return None


def format_semver(ver_tuple: tuple[int, int, int]) -> str:
    """Format version tuple as 'major.minor.patch'."""
    return f"{ver_tuple[0]}.{ver_tuple[1]}.{ver_tuple[2]}"


def select_deck_asset(assets: list[dict]) -> dict | None:
    """Find the best Windows x64 setup executable in Scrcpy Deck release assets."""
    candidates = []
    for asset in assets:
        name = asset.get("name", "")
        url = asset.get("browser_download_url", "")
        if not name or not url:
            continue
        lowered = name.lower()
        if (
            lowered.endswith(".exe")
            and "arm" not in lowered
            and "x86" not in lowered
            and "32-bit" not in lowered
            and "win32" not in lowered
        ):
            candidates.append(asset)

    if not candidates:
        return None

    def score(asset):
        name = asset.get("name", "").lower()
        pts = 0
        if "setup" in name or "installer" in name:
            pts += 10
        if "scrcpy" in name or "deck" in name:
            pts += 5
        if "x64" in name or "win64" in name:
            pts += 2
        return pts

    candidates.sort(key=score, reverse=True)
    return candidates[0]


def select_scrcpy_asset(assets: list[dict]) -> dict | None:
    """Find the official Windows 64-bit ZIP archive in scrcpy release assets."""
    # First search for asset containing win64 and ending with .zip
    for asset in assets:
        name = asset.get("name", "").lower()
        if "win64" in name and name.endswith(".zip"):
            return asset

    # Fallback to any windows zip if win64 not explicitly in name (e.g., windows64)
    for asset in assets:
        name = asset.get("name", "").lower()
        if ("windows" in name or "win" in name) and "32" not in name and "arm" not in name and name.endswith(".zip"):
            return asset

    return None


@dataclass
class ReleaseEntry:
    repo: str
    tag_name: str
    version_str: str
    version_tuple: tuple[int, int, int]
    name: str
    published_at: str
    body: str
    html_url: str
    prerelease: bool
    draft: bool
    asset_name: str | None
    download_url: str | None
    asset_size: int
    is_compatible_asset: bool

    @property
    def version(self) -> str:
        return self.version_str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["version_tuple"] = list(self.version_tuple)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ReleaseEntry":
        d = dict(data)
        if isinstance(d.get("version_tuple"), list):
            d["version_tuple"] = tuple(d["version_tuple"])
        return cls(**d)


def _fetch_release_page(repo: str, page: int, etag: str | None = None, timeout: int = 10):
    """Fetch a single page of releases from GitHub API."""
    url = f"https://api.github.com/repos/{repo}/releases?page={page}&per_page=30"
    headers = {
        "User-Agent": "ScrcpyDeck-VersionManager",
        "Accept": "application/vnd.github.v3+json",
    }
    if etag and page == 1:
        headers["If-None-Match"] = etag

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        new_etag = resp.headers.get("ETag") if page == 1 else None
        data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, dict):
            data = [data]
        return data, new_etag


class ReleaseCatalog:
    """Thread-safe release discovery service with pagination, ETag, and persistent caching."""

    def __init__(self, cache_file: Path = None):
        if cache_file is None:
            if CACHE_FILE is not None:
                cache_file = CACHE_FILE
            else:
                from assets import get_writable_runtime
                cache_file = get_writable_runtime().parent / "release_catalog_cache.json"
        self.cache_file = Path(cache_file)
        self._lock = threading.Lock()
        self._cache = self._load_cache()

    def _load_cache(self) -> dict:
        if self.cache_file.is_file():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {}

    def _save_cache(self):
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.cache_file.with_suffix(f".tmp_{os.getpid()}_{time.time()}")
            tmp.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")
            tmp.replace(self.cache_file)
        except Exception:
            pass

    def get_cached_releases(self, repo: str) -> list[ReleaseEntry]:
        """Return cached releases for repo without making network calls."""
        with self._lock:
            repo_cache = self._cache.get(repo, {})
            entries_data = repo_cache.get("releases", [])
            entries = []
            for item in entries_data:
                try:
                    entries.append(ReleaseEntry.from_dict(item))
                except Exception:
                    pass
            entries.sort(key=lambda r: r.version_tuple, reverse=True)
            return entries

    def is_cache_fresh(self, repo: str, max_age: int = CACHE_TTL_SECONDS) -> bool:
        """Check if cached data is within max_age seconds."""
        with self._lock:
            repo_cache = self._cache.get(repo, {})
            timestamp = repo_cache.get("timestamp", 0)
            return (time.time() - timestamp) < max_age and bool(repo_cache.get("releases"))

    def fetch_releases(
        self,
        repo: str,
        force_refresh: bool = False,
        timeout: int = 10,
        include_prereleases: bool = False,
        cancel_event: threading.Event | None = None,
        return_source: bool = False,
    ) -> tuple[list[ReleaseEntry], bool] | tuple[list[ReleaseEntry], bool, str]:
        """Fetch all releases with pagination from GitHub API.

        Returns ``(releases, is_cached)`` for backward compatibility.  When
        ``return_source`` is true, a third value identifies ``network``,
        ``cache``, ``not_modified``, or ``offline_cache``.
        """
        def result(entries, is_cached, source):
            if return_source:
                return entries, is_cached, source
            return entries, is_cached

        if not force_refresh and self.is_cache_fresh(repo):
            all_cached = self.get_cached_releases(repo)
            filtered = [r for r in all_cached if include_prereleases or not r.prerelease]
            return result(filtered, True, "cache")

        raw_releases = []
        etag = None
        with self._lock:
            repo_cache = self._cache.get(repo, {})
            etag = repo_cache.get("etag") if not force_refresh else None

        page = 1
        headers = {
            "User-Agent": "ScrcpyDeck-VersionManager",
            "Accept": "application/vnd.github.v3+json",
        }
        if etag and page == 1:
            headers["If-None-Match"] = etag

        try:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    raise InterruptedError("Release catalog request cancelled")
                try:
                    try:
                        res = _fetch_release_page(repo, page, etag=etag, timeout=timeout)
                    except TypeError:
                        res = _fetch_release_page(repo, page)
                    if isinstance(res, tuple):
                        data, new_etag = res
                        if page == 1 and new_etag:
                            etag = new_etag
                    else:
                        data = res
                    if not isinstance(data, list) or not data:
                        break
                    raw_releases.extend(data)
                    if len(data) < 30:
                        break
                    page += 1
                    if page > 100:  # Defensive cap; GitHub currently exposes far fewer.
                        break
                except urllib.error.HTTPError as http_err:
                    if http_err.code == 304 and page == 1:
                        # Cache is still valid!
                        with self._lock:
                            if repo in self._cache:
                                self._cache[repo]["timestamp"] = time.time()
                                self._save_cache()
                        all_cached = self.get_cached_releases(repo)
                        filtered = [r for r in all_cached if include_prereleases or not r.prerelease]
                        return result(filtered, True, "not_modified")
                    raise http_err

        except InterruptedError:
            raise
        except Exception:
            # On network/rate limit error, return cached releases if available
            all_cached = self.get_cached_releases(repo)
            if all_cached:
                filtered = [r for r in all_cached if include_prereleases or not r.prerelease]
                return result(filtered, True, "offline_cache")
            raise

        # Process retrieved releases
        parsed_entries = []
        is_deck = (repo.lower() == DECK_REPO.lower())

        seen_versions = set()
        for rel in raw_releases:
            if cancel_event is not None and cancel_event.is_set():
                raise InterruptedError("Release catalog request cancelled")
            if not isinstance(rel, dict):
                continue
            if rel.get("draft", False):
                continue
            if rel.get("prerelease", False) and not include_prereleases:
                continue
            tag = rel.get("tag_name", "")
            name = rel.get("name", "") or tag
            ver_tuple = parse_semver(tag) or parse_semver(name)
            if not ver_tuple:
                continue

            # Clean version string (e.g. "5.0.1" or "4.0.3")
            m = re.search(r"(\d+\.\d+(?:\.\d+)?)", tag) or re.search(r"(\d+\.\d+(?:\.\d+)?)", name)
            version_str = m.group(1) if m else format_semver(ver_tuple)
            if ver_tuple in seen_versions:
                continue
            seen_versions.add(ver_tuple)

            assets = rel.get("assets", [])
            if not isinstance(assets, list):
                assets = []
            chosen_asset = select_deck_asset(assets) if is_deck else select_scrcpy_asset(assets)

            entry = ReleaseEntry(
                repo=repo,
                tag_name=tag,
                version_str=version_str,
                version_tuple=ver_tuple,
                name=name,
                published_at=rel.get("published_at", ""),
                body=rel.get("body", "") or "",
                html_url=rel.get("html_url", f"https://github.com/{repo}/releases/tag/{tag}"),
                prerelease=bool(rel.get("prerelease", False)),
                draft=False,
                asset_name=chosen_asset["name"] if chosen_asset else None,
                download_url=chosen_asset["browser_download_url"] if chosen_asset else None,
                asset_size=chosen_asset.get("size", 0) if chosen_asset else 0,
                is_compatible_asset=bool(chosen_asset),
            )
            parsed_entries.append(entry)

        parsed_entries.sort(key=lambda r: r.version_tuple, reverse=True)

        # Update cache
        with self._lock:
            self._cache[repo] = {
                "timestamp": time.time(),
                "etag": etag,
                "releases": [e.to_dict() for e in parsed_entries],
            }
            self._save_cache()

        filtered = [r for r in parsed_entries if include_prereleases or not r.prerelease]
        return result(filtered, False, "network")


_default_catalog = None


def get_catalog(repo: str | None = None, force_refresh: bool = False, include_prereleases: bool = False):
    global _default_catalog
    target_cache_file = CACHE_FILE
    if _default_catalog is None:
        _default_catalog = ReleaseCatalog(cache_file=target_cache_file)
    elif target_cache_file is not None and _default_catalog.cache_file != Path(target_cache_file):
        _default_catalog = ReleaseCatalog(cache_file=target_cache_file)

    if repo is None:
        return _default_catalog

    if repo.lower() in ("deck", "scrcpydeck", DECK_REPO.lower()):
        target_repo = DECK_REPO
    elif repo.lower() in ("scrcpy", SCRCPY_REPO.lower()):
        target_repo = SCRCPY_REPO
    else:
        target_repo = repo

    releases, _ = _default_catalog.fetch_releases(
        target_repo,
        force_refresh=force_refresh,
        include_prereleases=include_prereleases,
    )
    return releases
