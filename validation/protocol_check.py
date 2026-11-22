"""Frozen protocol sanity + provenance hashes (engine freeze, R3).

Asserts the protocol file loads with all required fields, that the frozen
IAAFT settings and the harness fit-band rule are intact, and that the role
declaration / app-defaults difference are recorded. Prints the provenance
hashes (protocol sha256 + engine git commit) for the results record.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
from validation._common import Check, print_header  # noqa: E402
from validation import _protocol  # noqa: E402


def main() -> None:
    print_header("protocol_check")
    c = Check("protocol_check")

    data = _protocol.load_protocol()
    c.ok("protocol loads with all required fields",
         all(key in data for key in _protocol.REQUIRED_FIELDS),
         f"{len(data)} fields present, {len(_protocol.REQUIRED_FIELDS)} required")

    iaaft = data["iaaft"]
    assert isinstance(iaaft, dict)
    c.ok("IAAFT settings are the frozen ones",
         iaaft.get("n_surrogates") == 39 and iaaft.get("max_iter") == 500,
         f"n_surrogates={iaaft.get('n_surrogates')}, "
         f"max_iter={iaaft.get('max_iter')}")
    c.ok("IAAFT tolerance is the frozen one", iaaft.get("tol") == 1e-6,
         f"tol={iaaft.get('tol')}")

    fit_band = data["fit_band"]
    assert isinstance(fit_band, dict)
    c.ok("fit-band rule matches the harness standard",
         fit_band.get("rule") == "indices [lag.size // 8 : int(lag.size / 1.5)]",
         f"rule={fit_band.get('rule')}")

    c.ok("role declaration and app_defaults difference are recorded",
         isinstance(data["role"], str) and bool(data["role"])
         and isinstance(data["app_defaults"], dict)
         and "note" in data["app_defaults"],
         "role + app_defaults.note present")

    hashes = _protocol.protocol_hashes()
    print(f"protocol sha256: {hashes['protocol_sha256']}")
    print(f"engine commit  : {hashes['engine_commit']}")
    c.ok("hashes computed",
         len(hashes["protocol_sha256"]) == 64
         and len(hashes["engine_commit"]) == 40,
         f"sha256 {len(hashes['protocol_sha256'])} chars, "
         f"commit {len(hashes['engine_commit'])} chars")

    c.finish()


if __name__ == "__main__":
    main()
