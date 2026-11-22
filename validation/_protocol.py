"""Frozen analysis protocol: loading, validation, and provenance hashes.

The protocol (``iaaft_protocol.json``) is the source of truth for every
number reported in the thesis and for all IAAFT calibration results; the
interactive app's widget defaults differ and are recorded inside it
(``app_defaults``).
"""
import hashlib
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = Path(__file__).resolve().parent / "iaaft_protocol.json"

REQUIRED_FIELDS = (
    "description",
    "role",
    "app_defaults",
    "lag_grid",
    "q_grid",
    "fit_band",
    "order",
    "robust_width",
    "iaaft",
    "seed_policy",
    "preprocessing",
)


def load_protocol() -> dict[str, object]:
    """Load the protocol JSON and reject files with missing top-level fields."""
    raw = PROTOCOL_PATH.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("a protokoll fájlnak JSON objektumot kell tartalmaznia.")
    missing = [key for key in REQUIRED_FIELDS if key not in data]
    if missing:
        raise ValueError(
            f"a protokoll fájlból hiányoznak a kötelező mezők: {missing}"
        )
    return data


def protocol_hashes() -> dict[str, str]:
    """Return the sha256 of the protocol file bytes and the engine git commit."""
    raw = PROTOCOL_PATH.read_bytes()
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True
    ).strip()
    return {
        "protocol_sha256": hashlib.sha256(raw).hexdigest(),
        "engine_commit": commit,
    }
