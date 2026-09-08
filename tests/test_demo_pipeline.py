from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_safe_demo_pipeline(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "run_demo.py"),
            "--output-root",
            str(tmp_path),
        ],
        check=True,
        cwd=REPO_ROOT,
    )

    output = tmp_path / "sample_output"
    metrics = json.loads((output / "model_metrics.json").read_text(encoding="utf-8"))
    summary = json.loads((output / "incident_summary.json").read_text(encoding="utf-8"))
    forensic = json.loads((output / "plc_forensics_event.json").read_text(encoding="utf-8"))
    events = pd.read_csv(output / "events.csv")
    synthetic = tmp_path / "data" / "synthetic"
    process_normal = pd.read_csv(synthetic / "packaging_line_process_normal.csv")
    process_incident = pd.read_csv(synthetic / "packaging_line_process_incident.csv")
    network_normal = pd.read_csv(synthetic / "packaging_line_network_normal.csv")
    network_incident = pd.read_csv(synthetic / "packaging_line_network_incident.csv")
    truth = pd.read_csv(synthetic / "packaging_line_ground_truth.csv")

    assert len(process_normal) == 7_200
    assert len(process_incident) == 1_800
    assert len(network_normal) == 1_928
    assert len(network_incident) == 586
    assert len(truth) == 11
    for frame in (process_normal, process_incident, network_normal, network_incident, truth):
        timestamps = pd.to_datetime(frame["timestamp"], utc=True)
        assert timestamps.is_monotonic_increasing
    assert process_normal["safety_ok"].eq(1).all()
    assert process_incident["safety_ok"].eq(1).all()
    assert process_incident["estop"].eq(0).all()
    assert process_normal["jam_timeout_s"].eq(5).all()
    assert set(process_incident["jam_timeout_s"]) == {5, 20}
    assert process_incident["actual_speed_pct"].between(0, 100).all()
    assert process_incident["motor_current_a"].between(0, 35).all()
    assert process_incident["vibration_mm_s"].between(0, 12).all()
    assert process_incident["motor_current_a"].max() >= 20
    assert {
        "NORMAL",
        "SUSPICIOUS_RECON",
        "PLC_CHANGE",
        "POST_CHANGE",
        "PROCESS_IMPACT",
        "RECOVERY",
    }.issubset(set(process_incident["ground_truth_label"]))

    assert metrics["incident_anomaly_max"] >= 75
    assert metrics["incident_anomaly_max"] > metrics["normal_anomaly_p95"]
    assert metrics["normal_alert_rate_at_75"] <= 0.10
    assert metrics["incident_windows_at_or_above_75"] >= 1
    assert forensic["changed"] is True
    assert forensic["changed_artifact_count"] >= 1
    assert summary["severity"] == "CRITICAL"
    assert summary["risk_score"] == 100
    assert {
        "new_source",
        "scan_like",
        "network_anomaly",
        "programming_activity",
        "plc_artifact_change",
    }.issubset(set(events["event_type"]))
