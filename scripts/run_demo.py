from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from common import REPO_ROOT


def run(*parts: str | Path) -> None:
    command = [sys.executable, *(str(part) for part in parts)]
    print("+", " ".join(command))
    subprocess.run(command, check=True, cwd=REPO_ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the safe synthetic OT Sentinel demo.")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "lab.example.json")
    args = parser.parse_args()
    root = args.output_root.resolve()

    run(
        REPO_ROOT / "scripts" / "generate_sample_data.py",
        "--config",
        args.config,
        "--output-root",
        root,
    )
    run(
        REPO_ROOT / "scripts" / "build_features.py",
        "--config",
        args.config,
        "--input",
        root / "data" / "features" / "malcolm_normal_sessions.csv",
        "--output",
        root / "data" / "features" / "normal_windows.csv",
    )
    run(
        REPO_ROOT / "scripts" / "build_features.py",
        "--config",
        args.config,
        "--input",
        root / "data" / "features" / "malcolm_incident_sessions.csv",
        "--output",
        root / "data" / "features" / "incident_windows.csv",
    )
    run(
        REPO_ROOT / "model" / "train_isolation_forest.py",
        "--normal",
        root / "data" / "features" / "normal_windows.csv",
        "--incident",
        root / "data" / "features" / "incident_windows.csv",
        "--output-dir",
        root / "model",
        "--scored-output-dir",
        root / "sample_output",
    )
    run(
        REPO_ROOT / "scripts" / "icspector_manifest.py",
        "--config",
        args.config,
        "--baseline-dir",
        root / "artifacts" / "icspector" / "baseline",
        "--incident-dir",
        root / "artifacts" / "icspector" / "incident",
        "--manifest-output-dir",
        root / "artifacts" / "icspector",
        "--event-output",
        root / "sample_output" / "plc_forensics_event.json",
        "--timestamp",
        "2026-09-01T14:13:00Z",
    )
    run(
        REPO_ROOT / "scripts" / "correlate_events.py",
        "--config",
        args.config,
        "--scored-incident",
        root / "sample_output" / "scored_incident_windows.csv",
        "--plc-event",
        root / "sample_output" / "plc_forensics_event.json",
        "--events-output",
        root / "sample_output" / "events.csv",
        "--summary-output",
        root / "sample_output" / "incident_summary.json",
    )
    print("\nDemo pipeline complete.")
    print(f"Dashboard command: streamlit run {REPO_ROOT / 'dashboard' / 'app.py'}")


if __name__ == "__main__":
    main()
