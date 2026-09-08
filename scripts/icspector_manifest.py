from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from common import REPO_ROOT, load_config


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest(snapshot_dir: Path, snapshot_name: str, generated_at: str) -> dict:
    if not snapshot_dir.is_dir():
        raise FileNotFoundError(f"Snapshot directory not found: {snapshot_dir}")
    artifacts = []
    for path in sorted(candidate for candidate in snapshot_dir.rglob("*") if candidate.is_file()):
        artifacts.append(
            {
                "relative_path": path.relative_to(snapshot_dir).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return {
        "snapshot": snapshot_name,
        "snapshot_dir": str(snapshot_dir.resolve()),
        "generated_at": generated_at,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }


def compare(before: dict, after: dict) -> dict:
    old = {item["relative_path"]: item for item in before["artifacts"]}
    new = {item["relative_path"]: item for item in after["artifacts"]}
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    modified = sorted(
        path for path in old.keys() & new.keys() if old[path]["sha256"] != new[path]["sha256"]
    )
    return {
        "changed": bool(added or removed or modified),
        "changed_artifact_count": len(added) + len(removed) + len(modified),
        "added": added,
        "removed": removed,
        "modified": modified,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hash and compare two ICSpector-exported artifact snapshots."
    )
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--incident-dir", type=Path, required=True)
    parser.add_argument("--manifest-output-dir", type=Path, required=True)
    parser.add_argument("--event-output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--timestamp", default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    generated_at = args.timestamp or datetime.now(timezone.utc).isoformat()
    baseline = manifest(args.baseline_dir, "baseline", generated_at)
    incident = manifest(args.incident_dir, "incident", generated_at)
    comparison = compare(baseline, incident)

    args.manifest_output_dir.mkdir(parents=True, exist_ok=True)
    (args.manifest_output_dir / "baseline_manifest.json").write_text(
        json.dumps(baseline, indent=2), encoding="utf-8"
    )
    (args.manifest_output_dir / "incident_manifest.json").write_text(
        json.dumps(incident, indent=2), encoding="utf-8"
    )

    event = {
        "timestamp": generated_at,
        "plc_ip": config["plc_ip"],
        "asset": config["asset_name"],
        "snapshot_before": "baseline",
        "snapshot_after": "incident",
        **comparison,
        "change_summary": (
            "ICSpector-exported artifact snapshots differ."
            if comparison["changed"]
            else "No ICSpector-exported artifact difference found."
        ),
        "confidence": "high" if comparison["changed"] else "low",
    }
    args.event_output.parent.mkdir(parents=True, exist_ok=True)
    args.event_output.write_text(json.dumps(event, indent=2), encoding="utf-8")
    print(json.dumps(event, indent=2))


if __name__ == "__main__":
    main()

