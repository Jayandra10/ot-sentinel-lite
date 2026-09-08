from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from common import REPO_ROOT, load_config, severity_for_score


EVENT_COLUMNS = [
    "timestamp",
    "event_type",
    "asset",
    "source",
    "severity",
    "score",
    "summary",
]


def event(timestamp, event_type, asset, source, severity, score, summary) -> dict:
    return {
        "timestamp": timestamp,
        "event_type": event_type,
        "asset": asset,
        "source": source,
        "severity": severity,
        "score": round(float(score), 2),
        "summary": summary,
    }


def first_matching(frame: pd.DataFrame, mask: pd.Series) -> pd.Series | None:
    matches = frame.loc[mask].sort_values("window_start")
    return None if matches.empty else matches.iloc[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fuse network, model, and PLC evidence.")
    parser.add_argument("--scored-incident", type=Path, required=True)
    parser.add_argument("--plc-event", type=Path, required=True)
    parser.add_argument("--events-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    windows = pd.read_csv(args.scored_incident)
    required = {
        "window_start",
        "src_ip",
        "new_source",
        "unique_dst_ports",
        "conn_count",
        "anomaly_score",
        "suricata_alert",
        "programming_activity",
    }
    missing = sorted(required - set(windows.columns))
    if missing:
        raise ValueError(f"Scored incident data is missing: {', '.join(missing)}")
    plc_event = json.loads(args.plc_event.read_text(encoding="utf-8"))
    points = config["risk_points"]
    asset = config["asset_name"]
    events: list[dict] = []
    flags: dict[str, bool] = {}

    new_source = first_matching(windows, windows["new_source"] == 1)
    flags["new_source"] = new_source is not None
    if new_source is not None:
        events.append(
            event(
                new_source["window_start"],
                "new_source",
                asset,
                "Malcolm",
                "MEDIUM",
                points["new_source"],
                f"New source {new_source['src_ip']} contacted the PLC.",
            )
        )

    scan_mask = (windows["unique_dst_ports"] >= config["scan_unique_port_threshold"]) | (
        windows["conn_count"] >= config["scan_connection_threshold"]
    )
    scan_like = first_matching(windows, scan_mask)
    flags["scan_like"] = scan_like is not None
    if scan_like is not None:
        events.append(
            event(
                scan_like["window_start"],
                "scan_like",
                asset,
                "Malcolm",
                "MEDIUM",
                points["scan_like"],
                "Scan-like PLC connection window exceeded the configured threshold.",
            )
        )

    anomaly_matches = windows.loc[windows["anomaly_score"] >= config["anomaly_threshold"]]
    flags["ai_anomaly"] = not anomaly_matches.empty
    if not anomaly_matches.empty:
        anomaly = anomaly_matches.sort_values("anomaly_score", ascending=False).iloc[0]
        events.append(
            event(
                anomaly["window_start"],
                "network_anomaly",
                asset,
                "IsolationForest",
                severity_for_score(anomaly["anomaly_score"]),
                anomaly["anomaly_score"],
                "PLC-facing network window is anomalous relative to the normal baseline.",
            )
        )

    alert = first_matching(windows, windows["suricata_alert"] == 1)
    flags["suricata_alert"] = alert is not None
    if alert is not None:
        events.append(
            event(
                alert["window_start"],
                "suricata_alert",
                asset,
                "Malcolm",
                "MEDIUM",
                points["suricata_alert"],
                "A Suricata alert overlaps the PLC-facing evidence window.",
            )
        )

    programming = first_matching(windows, windows["programming_activity"] == 1)
    flags["programming_activity"] = programming is not None
    if programming is not None:
        events.append(
            event(
                programming["window_start"],
                "programming_activity",
                asset,
                "Malcolm",
                "HIGH",
                points["programming_activity"],
                "Observed lab-labelled CODESYS programming/download activity.",
            )
        )

    flags["plc_artifact_change"] = bool(plc_event.get("changed"))
    if flags["plc_artifact_change"]:
        events.append(
            event(
                plc_event["timestamp"],
                "plc_artifact_change",
                asset,
                "ICSpector",
                "HIGH",
                points["plc_artifact_change"],
                plc_event["change_summary"],
            )
        )

    risk_score = min(
        100,
        sum(int(points[name]) for name, present in flags.items() if present),
    )
    severity = severity_for_score(risk_score)
    reasons = [name for name, present in flags.items() if present]
    verdict = (
        "Correlated network anomaly and PLC artifact change require investigation."
        if flags["ai_anomaly"] and flags["plc_artifact_change"]
        else "Evidence is incomplete; review individual signals."
    )

    observed_sources = set(windows["src_ip"].astype(str))
    assets = [
        {"name": asset, "ip": config["plc_ip"], "trust": "Known", "state": "Observed"},
        {
            "name": "Engineering PC",
            "ip": config["engineering_ip"],
            "trust": "Known",
            "state": "Observed" if config["engineering_ip"] in observed_sources else "Not observed",
        },
        {
            "name": "Rogue host",
            "ip": config["rogue_ip"],
            "trust": "New",
            "state": "Observed" if config["rogue_ip"] in observed_sources else "Not observed",
        },
    ]

    events_frame = pd.DataFrame(events, columns=EVENT_COLUMNS)
    if not events_frame.empty:
        events_frame = events_frame.sort_values("timestamp")
    args.events_output.parent.mkdir(parents=True, exist_ok=True)
    events_frame.to_csv(args.events_output, index=False)

    summary = {
        "asset": asset,
        "risk_score": risk_score,
        "severity": severity,
        "verdict": verdict,
        "reasons": reasons,
        "evidence_flags": flags,
        "assets": assets,
        "event_count": len(events_frame),
    }
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

