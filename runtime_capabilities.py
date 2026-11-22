"""Centralized capability and compatibility detection for Genymobile scrcpy."""
from dataclasses import asdict, dataclass
from pathlib import Path
import re
import subprocess
import threading

from release_catalog import parse_semver


@dataclass
class FeatureRequirement:
    name: str
    display_name: str
    min_version: str  # e.g. "4.0"
    cli_flags: tuple[str, ...]  # e.g. ("--camera-torch",)
    is_optional: bool
    explanation: str


# Static capability registry based on verified upstream scrcpy release history
FEATURE_REGISTRY: dict[str, FeatureRequirement] = {
    "camera_torch": FeatureRequirement(
        name="camera_torch",
        display_name="Camera torch",
        min_version="4.0",
        cli_flags=("--camera-torch",),
        is_optional=True,
        explanation="Camera torch requires scrcpy 4.0 or newer.",
    ),
    "camera_zoom": FeatureRequirement(
        name="camera_zoom",
        display_name="Camera zoom",
        min_version="4.0",
        cli_flags=("--camera-zoom",),
        is_optional=True,
        explanation="Camera zoom requires scrcpy 4.0 or newer.",
    ),
    "camera_source": FeatureRequirement(
        name="camera_source",
        display_name="Camera capture",
        min_version="2.0",
        cli_flags=("--video-source=camera", "--video-source"),
        is_optional=False,
        explanation="Camera capture requires scrcpy 2.0 or newer.",
    ),
    "camera_facing": FeatureRequirement(
        name="camera_facing",
        display_name="Camera facing selection",
        min_version="2.0",
        cli_flags=("--camera-facing",),
        is_optional=True,
        explanation="Camera facing requires scrcpy 2.0 or newer.",
    ),
    "camera_ar": FeatureRequirement(
        name="camera_ar",
        display_name="Camera aspect ratio",
        min_version="2.0",
        cli_flags=("--camera-ar",),
        is_optional=True,
        explanation="Camera aspect ratio requires scrcpy 2.0 or newer.",
    ),
    "camera_fps": FeatureRequirement(
        name="camera_fps",
        display_name="Camera frame rate",
        min_version="2.0",
        cli_flags=("--camera-fps",),
        is_optional=True,
        explanation="Camera frame rate requires scrcpy 2.0 or newer.",
    ),
    "camera_id": FeatureRequirement(
        name="camera_id",
        display_name="Specific camera lens selection",
        min_version="2.0",
        cli_flags=("--camera-id",),
        is_optional=True,
        explanation="Selecting camera lens ID requires scrcpy 2.0 or newer.",
    ),
    "audio_forward": FeatureRequirement(
        name="audio_forward",
        display_name="Audio forwarding",
        min_version="2.0",
        cli_flags=("--audio-codec", "--no-audio"),
        is_optional=True,
        explanation="Audio forwarding was introduced in scrcpy 2.0.",
    ),
    "mic_only": FeatureRequirement(
        name="mic_only",
        display_name="Microphone capture",
        min_version="2.0",
        cli_flags=("--audio-source=mic",),
        is_optional=False,
        explanation="Microphone capture requires scrcpy 2.0 or newer.",
    ),
    "uhid_input": FeatureRequirement(
        name="uhid_input",
        display_name="UHID simulation mode",
        min_version="2.0",
        cli_flags=("--keyboard=uhid", "--mouse=uhid"),
        is_optional=False,
        explanation="UHID keyboard and mouse simulation requires scrcpy 2.0 or newer.",
    ),
    "otg_mode": FeatureRequirement(
        name="otg_mode",
        display_name="OTG mode",
        min_version="2.0",
        cli_flags=("--otg",),
        is_optional=False,
        explanation="Physical OTG keyboard and mouse mode requires scrcpy 2.0 or newer.",
    ),
    "capture_orientation": FeatureRequirement(
        name="capture_orientation",
        display_name="Capture orientation",
        min_version="2.1",
        cli_flags=("--capture-orientation",),
        is_optional=True,
        explanation="Capture orientation (@angle) requires scrcpy 2.1 or newer.",
    ),
    "codec_h265": FeatureRequirement(
        name="codec_h265",
        display_name="H.265 video codec",
        min_version="1.22",
        cli_flags=("--video-codec=h265",),
        is_optional=True,
        explanation="H.265 video codec requires scrcpy 1.22 or newer.",
    ),
    "codec_av1": FeatureRequirement(
        name="codec_av1",
        display_name="AV1 video codec",
        min_version="2.0",
        cli_flags=("--video-codec=av1",),
        is_optional=True,
        explanation="AV1 video codec requires scrcpy 2.0 or newer.",
    ),
    "hardware_decoder": FeatureRequirement(
        name="hardware_decoder",
        display_name="Hardware decoder selection",
        min_version="5.0",
        cli_flags=("--video-codec-options",),
        is_optional=True,
        explanation="Advanced hardware decoder selection requires scrcpy 5.0 or newer.",
    ),
    "turn_screen_off": FeatureRequirement(
        name="turn_screen_off",
        display_name="Turn screen off",
        min_version="1.14",
        cli_flags=("--turn-screen-off",),
        is_optional=True,
        explanation="Turning the physical screen off requires scrcpy 1.14 or newer.",
    ),
    "stay_awake": FeatureRequirement(
        name="stay_awake",
        display_name="Stay awake",
        min_version="1.13",
        cli_flags=("--stay-awake",),
        is_optional=True,
        explanation="Stay awake requires scrcpy 1.13 or newer.",
    ),
    "show_touches": FeatureRequirement(
        name="show_touches",
        display_name="Show touches",
        min_version="1.10",
        cli_flags=("--show-touches",),
        is_optional=True,
        explanation="Show touch points requires scrcpy 1.10 or newer.",
    ),
}

# Cache for executable CLI help output: {exe_path: set_of_supported_flags}
_CLI_FLAG_CACHE: dict[str, set[str]] = {}
_CLI_CACHE_LOCK = threading.Lock()


def probe_cli_flags(scrcpy_exe: str | Path, timeout: float = 3.0) -> set[str]:
    """Inspect scrcpy executable's supported CLI flags using `scrcpy --help`."""
    if not scrcpy_exe:
        return set()
    exe_str = str(Path(scrcpy_exe).resolve())
    with _CLI_CACHE_LOCK:
        if exe_str in _CLI_FLAG_CACHE:
            return _CLI_FLAG_CACHE[exe_str]

    if not Path(exe_str).is_file():
        return set()

    flags = set()
    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        res = subprocess.run(
            [exe_str, "--help"],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=creationflags,
        )
        combined = (res.stdout or "") + "\n" + (res.stderr or "")
        # Find all tokens starting with --
        found_flags = re.findall(r"(--[a-zA-Z0-9_\-]+(?:=[a-zA-Z0-9_\-]+)?)", combined)
        for f in found_flags:
            flags.add(f.split("=")[0])  # base flag
            flags.add(f)  # exact flag
    except Exception:
        pass

    with _CLI_CACHE_LOCK:
        _CLI_FLAG_CACHE[exe_str] = flags
    return flags


def invalidate_cli_cache(scrcpy_exe: str | Path = None):
    """Invalidate cached CLI flags."""
    with _CLI_CACHE_LOCK:
        if scrcpy_exe:
            _CLI_FLAG_CACHE.pop(str(Path(scrcpy_exe).resolve()), None)
        else:
            _CLI_FLAG_CACHE.clear()


def check_feature_support(
    feature_name: str,
    runtime_version_str: str,
    scrcpy_exe: str | Path = None,
) -> dict:
    """Evaluate support for a single feature based on version and CLI probe.

    Returns dict matching the required capability schema:
    {
        "supported": bool,
        "status": "supported" | "unsupported" | "unknown",
        "required_version": str,
        "current_version": str,
        "reason": str,
        "is_optional": bool
    }
    """
    if isinstance(runtime_version_str, Path) or (
        isinstance(runtime_version_str, str)
        and (runtime_version_str.endswith(".exe") or "/" in runtime_version_str or "\\" in runtime_version_str)
    ):
        scrcpy_exe, runtime_version_str = runtime_version_str, str(scrcpy_exe or "")
    req = FEATURE_REGISTRY.get(feature_name)
    if not req:
        return {
            "supported": True,
            "status": "supported",
            "required_version": "1.0",
            "current_version": str(runtime_version_str or ""),
            "reason": "",
            "is_optional": True,
        }

    current_tuple = parse_semver(runtime_version_str)
    required_tuple = parse_semver(req.min_version)

    if not current_tuple or not required_tuple:
        return {
            "supported": False,
            "status": "unknown",
            "required_version": req.min_version,
            "current_version": str(runtime_version_str or "unknown"),
            "reason": f"Cannot determine version for {req.display_name}.",
            "is_optional": req.is_optional,
        }

    # First check semantic version
    version_supported = current_tuple >= required_tuple

    # Second check: if an executable is provided, optionally corroborate via CLI probing
    cli_flags = probe_cli_flags(scrcpy_exe) if scrcpy_exe else set()
    if cli_flags and req.cli_flags:
        # Check if any required base flag is recognized
        flag_recognized = any(
            flag in cli_flags or flag.split("=")[0] in cli_flags
            for flag in req.cli_flags
        )
        if flag_recognized:
            version_supported = True

    if version_supported:
        return {
            "supported": True,
            "status": "supported",
            "required_version": req.min_version,
            "current_version": str(runtime_version_str),
            "reason": "",
            "is_optional": req.is_optional,
        }
    else:
        return {
            "supported": False,
            "status": "unsupported",
            "required_version": req.min_version,
            "current_version": str(runtime_version_str),
            "reason": req.explanation,
            "is_optional": req.is_optional,
        }


def get_all_capabilities(runtime_version_str: str, scrcpy_exe: str | Path = None) -> dict:
    """Return dictionary of all capability states for QML and backend consumption."""
    results = {}
    for feat in FEATURE_REGISTRY:
        results[feat] = check_feature_support(feat, runtime_version_str, scrcpy_exe)
    return results


def summarize_incompatibilities(capabilities: dict) -> list[str]:
    """Return human-readable summaries of unavailable features."""
    issues = []
    if not capabilities.get("camera_torch", {}).get("supported", True) or not capabilities.get("camera_zoom", {}).get("supported", True):
        issues.append("Some camera features (torch, zoom) are unavailable.")
    if not capabilities.get("camera_source", {}).get("supported", True):
        issues.append("Camera capture is not supported in this runtime.")
    if not capabilities.get("audio_forward", {}).get("supported", True):
        issues.append("Audio forwarding is not supported in this runtime.")
    if not capabilities.get("uhid_input", {}).get("supported", True):
        issues.append("UHID input mode is not supported in this runtime.")
    if not capabilities.get("codec_av1", {}).get("supported", True):
        issues.append("AV1 codec is not supported in this runtime.")
    return issues
