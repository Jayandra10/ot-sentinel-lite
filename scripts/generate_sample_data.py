from __future__ import annotations

import argparse
import csv
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common import REPO_ROOT, SESSION_COLUMNS, load_config


PROCESS_COLUMNS = [
    "timestamp", "scenario", "asset", "plc_ip", "recipe_id", "operator_mode",
    "line_state", "conveyor_run", "safety_ok", "estop", "photoeye_infeed",
    "photoeye_outfeed", "jam_sensor", "fault_lamp", "fault_code",
    "jam_timeout_s", "speed_setpoint_pct", "actual_speed_pct",
    "motor_current_a", "vibration_mm_s", "temperature_c", "line_rate_ppm",
    "item_count", "reject_count", "reject_rate_pct", "plc_cycle_ms",
    "network_rx_kbps", "network_tx_kbps", "ground_truth_label",
]

GROUND_TRUTH_COLUMNS = [
    "timestamp", "event_id", "event_type", "actor", "asset", "severity",
    "label", "description", "expected_network_signal", "expected_process_signal",
]

DICTIONARY_COLUMNS = [
    "dataset", "column", "data_type", "unit", "description",
    "normal_behavior", "incident_behavior",
]


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def bounded(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def process_rows(
    config: dict,
    rng: random.Random,
    start: datetime,
    seconds: int,
    *,
    incident: bool,
) -> list[dict]:
    rows: list[dict] = []
    item_count = 125_000 if not incident else 178_500
    reject_count = 620 if not incident else 884
    item_accumulator = 0.0

    for offset in range(seconds):
        timestamp = start + timedelta(seconds=offset)
        recipe_id = "PKG-A12" if offset < 1_800 or incident else "PKG-B07"
        label = "NORMAL"
        line_state = "RUN"
        conveyor_run = 1
        jam_sensor = 0
        fault_lamp = 0
        fault_code = ""
        jam_timeout_s = 5
        speed_setpoint = 78.0 + 2.0 * math.sin(offset / 420.0)
        process_impact = False

        if not incident:
            if 1_800 <= offset < 1_920:
                line_state = "CHANGEOVER"
                conveyor_run = 0
                speed_setpoint = 0.0
            elif 4_800 <= offset < 4_860:
                line_state = "PLANNED_STOP"
                conveyor_run = 0
                speed_setpoint = 0.0
            if any(start_tick <= offset < start_tick + 4 for start_tick in (1_200, 3_600, 6_000)):
                jam_sensor = 1
        else:
            if 600 <= offset < 720:
                label = "SUSPICIOUS_RECON"
            elif 720 <= offset < 780:
                label = "PLC_CHANGE"
            elif 780 <= offset < 900:
                label = "POST_CHANGE"
            elif 900 <= offset < 1_080:
                label = "PROCESS_IMPACT"
                process_impact = True
            elif 1_080 <= offset < 1_200:
                label = "RECOVERY"
            elif offset >= 1_200:
                label = "POST_CHANGE"

            if offset >= 780:
                jam_timeout_s = 20
            if 900 <= offset < 920:
                jam_sensor = 1
                line_state = "JAM_DEVELOPING"
            elif 920 <= offset < 1_080:
                jam_sensor = 1
                fault_lamp = 1
                fault_code = "JAM_TIMEOUT"
                line_state = "FAULT"
                conveyor_run = 0
                speed_setpoint = 0.0
            elif 1_080 <= offset < 1_110:
                line_state = "RESETTING"
                conveyor_run = 0
                speed_setpoint = 0.0
            elif 1_110 <= offset < 1_140:
                line_state = "STARTING"
                speed_setpoint = 55.0

        if conveyor_run:
            actual_speed = speed_setpoint + rng.gauss(0.0, 0.8)
            motor_current = 4.2 + 0.11 * actual_speed + rng.gauss(0.0, 0.35)
            vibration = 0.9 + 0.018 * actual_speed + rng.gauss(0.0, 0.08)
            temperature = 41.5 + 0.065 * actual_speed + 0.002 * (offset % 600) + rng.gauss(0.0, 0.3)
            line_rate = actual_speed * 1.18 + rng.gauss(0.0, 1.8)
        else:
            actual_speed = 0.0
            motor_current = bounded(rng.gauss(0.6, 0.12), 0.2, 1.1)
            vibration = bounded(rng.gauss(0.18, 0.04), 0.05, 0.35)
            temperature = 42.0 + rng.gauss(0.0, 0.25)
            line_rate = 0.0

        if jam_sensor and conveyor_run:
            jam_age = max(0, offset - 900) if incident else 1
            actual_speed = bounded(67.0 - 1.1 * jam_age + rng.gauss(0.0, 1.2), 44.0, 68.0)
            motor_current = bounded(20.0 + 0.25 * jam_age + rng.gauss(0.0, 0.8), 19.0, 27.0)
            vibration = bounded(5.2 + 0.12 * jam_age + rng.gauss(0.0, 0.25), 4.8, 7.8)
            temperature = 49.0 + 0.08 * jam_age + rng.gauss(0.0, 0.35)
            line_rate = bounded(62.0 - 1.6 * jam_age + rng.gauss(0.0, 2.0), 25.0, 64.0)

        if line_state == "STARTING":
            ramp = (offset - 1_110) / 30.0
            actual_speed = bounded(20.0 + 35.0 * ramp + rng.gauss(0.0, 0.8), 18.0, 56.0)
            line_rate = actual_speed * 0.95

        actual_speed = bounded(actual_speed, 0.0, 100.0)
        motor_current = bounded(motor_current, 0.0, 35.0)
        vibration = bounded(vibration, 0.0, 12.0)
        temperature = bounded(temperature, 20.0, 90.0)
        line_rate = bounded(line_rate, 0.0, 130.0)

        item_accumulator += line_rate / 60.0
        produced = int(item_accumulator)
        item_accumulator -= produced
        item_count += produced
        reject_probability = 0.006 if not process_impact else 0.09
        rejected = sum(1 for _ in range(produced) if rng.random() < reject_probability)
        reject_count += rejected
        reject_rate_pct = bounded(
            (0.55 if not process_impact else 8.5)
            + rng.gauss(0.0, 0.12 if not process_impact else 0.8),
            0.0,
            20.0,
        )

        programming_window = incident and 750 <= offset < 810
        network_rx = rng.uniform(9.0, 18.0) + (rng.uniform(180, 420) if programming_window else 0)
        network_tx = rng.uniform(6.0, 14.0) + (rng.uniform(120, 360) if programming_window else 0)
        plc_cycle = rng.gauss(10.2, 0.55) + (rng.uniform(2.0, 6.0) if programming_window else 0)

        rows.append({
            "timestamp": timestamp.isoformat(),
            "scenario": "INCIDENT" if incident else "NORMAL_BASELINE",
            "asset": config["asset_name"],
            "plc_ip": config["plc_ip"],
            "recipe_id": recipe_id,
            "operator_mode": "AUTO",
            "line_state": line_state,
            "conveyor_run": conveyor_run,
            "safety_ok": 1,
            "estop": 0,
            "photoeye_infeed": 1 if produced else 0,
            "photoeye_outfeed": 1 if produced and offset % 2 == 0 else 0,
            "jam_sensor": jam_sensor,
            "fault_lamp": fault_lamp,
            "fault_code": fault_code,
            "jam_timeout_s": jam_timeout_s,
            "speed_setpoint_pct": round(speed_setpoint, 2),
            "actual_speed_pct": round(actual_speed, 2),
            "motor_current_a": round(motor_current, 3),
            "vibration_mm_s": round(vibration, 3),
            "temperature_c": round(temperature, 2),
            "line_rate_ppm": round(line_rate, 2),
            "item_count": item_count,
            "reject_count": reject_count,
            "reject_rate_pct": round(reject_rate_pct, 3),
            "plc_cycle_ms": round(plc_cycle, 3),
            "network_rx_kbps": round(network_rx, 2),
            "network_tx_kbps": round(network_tx, 2),
            "ground_truth_label": label,
        })
    return rows


def session(
    timestamp: datetime,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    *,
    service: str,
    duration: float,
    orig_bytes: int,
    resp_bytes: int,
    conn_state: str = "SF",
    suricata_alert: int = 0,
    programming_activity: int = 0,
) -> dict:
    return {
        "timestamp": timestamp.isoformat(),
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": src_port,
        "dst_port": dst_port,
        "proto": "tcp",
        "service": service,
        "duration": round(duration, 4),
        "orig_bytes": orig_bytes,
        "resp_bytes": resp_bytes,
        "conn_state": conn_state,
        "suricata_alert": suricata_alert,
        "programming_activity": programming_activity,
    }


def baseline_network(config: dict, rng: random.Random, start: datetime, seconds: int) -> list[dict]:
    rows: list[dict] = []
    for offset in range(0, seconds, 5):
        rows.append(session(
            start + timedelta(seconds=offset), config["hmi_ip"], config["plc_ip"],
            rng.randint(49152, 65000), 502, service="modbus",
            duration=rng.uniform(0.015, 0.06), orig_bytes=rng.randint(70, 130),
            resp_bytes=rng.randint(90, 220),
        ))
    for offset in range(0, seconds, 15):
        rows.append(session(
            start + timedelta(seconds=offset + 2), config["historian_ip"], config["plc_ip"],
            rng.randint(49152, 65000), 4840, service="opcua",
            duration=rng.uniform(0.04, 0.18), orig_bytes=rng.randint(180, 420),
            resp_bytes=rng.randint(260, 900),
        ))
    for offset in range(0, seconds, 900):
        rows.append(session(
            start + timedelta(seconds=offset + 20), config["engineering_ip"], config["plc_ip"],
            rng.randint(49152, 65000), rng.choice(config["programming_ports"]),
            service="codesys", duration=rng.uniform(0.12, 0.65),
            orig_bytes=rng.randint(280, 900), resp_bytes=rng.randint(350, 1_400),
        ))
    return sorted(rows, key=lambda record: record["timestamp"])


def incident_network(config: dict, rng: random.Random, start: datetime, seconds: int) -> list[dict]:
    rows = baseline_network(config, rng, start, seconds)
    scan_ports = [22, 80, 443, 502, 4840, 11740, 1217, 8080]
    for offset in range(72):
        rows.append(session(
            start + timedelta(seconds=600 + offset // 2), config["rogue_ip"], config["plc_ip"],
            43000 + offset, scan_ports[offset % len(scan_ports)], service="unknown",
            duration=rng.uniform(0.004, 0.07), orig_bytes=rng.randint(40, 150),
            resp_bytes=rng.randint(0, 100), conn_state="REJ" if offset % 2 else "S0",
            suricata_alert=1 if offset == 0 else 0,
        ))
    for offset in range(32):
        rows.append(session(
            start + timedelta(seconds=750 + offset * 2), config["engineering_ip"], config["plc_ip"],
            52000 + offset, config["programming_ports"][offset % len(config["programming_ports"])],
            service="codesys", duration=rng.uniform(0.8, 2.6),
            orig_bytes=rng.randint(5_000, 18_000), resp_bytes=rng.randint(3_000, 12_000),
            programming_activity=1,
        ))
    return sorted(rows, key=lambda record: record["timestamp"])


def ground_truth(start: datetime, config: dict) -> list[dict]:
    events = [
        (0, "GT-001", "baseline_start", "Operator", "INFO", "NORMAL", "Packaging line enters stable automatic production.", "Known HMI/historian polling only.", "Process values remain within baseline."),
        (600, "GT-002", "new_source", "Maintenance laptop", "MEDIUM", "SUSPICIOUS_RECON", "Previously unseen maintenance laptop contacts PLC services.", "New source IP appears.", "No immediate process effect."),
        (605, "GT-003", "scan_like", "Maintenance laptop", "MEDIUM", "SUSPICIOUS_RECON", "Narrow multi-port connection sweep targets the PLC.", "High connection count, port diversity, and failed states.", "No immediate process effect."),
        (750, "GT-004", "program_download", "Engineering workstation", "HIGH", "PLC_CHANGE", "CODESYS project download begins.", "Programming ports and unusually large transfers.", "PLC cycle and network throughput increase."),
        (780, "GT-005", "parameter_change", "Engineering workstation", "HIGH", "POST_CHANGE", "Jam_Timeout changes from 5 seconds to 20 seconds.", "Programming session ends.", "jam_timeout_s changes from 5 to 20."),
        (780, "GT-006", "artifact_change", "ICSpector simulator", "HIGH", "POST_CHANGE", "Synthetic PLC forensic snapshot differs from baseline.", "Not a packet-only finding.", "Configuration value differs."),
        (900, "GT-007", "jam_begins", "Packaging process", "HIGH", "PROCESS_IMPACT", "Carton accumulation activates the jam sensor.", "Ordinary HMI/historian traffic continues.", "Current and vibration rise while speed and throughput fall."),
        (905, "GT-008", "expected_baseline_trip", "Reference logic", "HIGH", "PROCESS_IMPACT", "Baseline five-second timeout would have faulted here.", "No separate network signal.", "Controller continues because timeout is now 20 seconds."),
        (920, "GT-009", "delayed_fault", "PLC01", "CRITICAL", "PROCESS_IMPACT", "Twenty-second jam timeout expires and the conveyor stops.", "No separate network signal.", "Fault lamp, JAM_TIMEOUT, zero speed, and zero line rate."),
        (1080, "GT-010", "operator_reset", "Operator", "MEDIUM", "RECOVERY", "Operator clears the jam and resets the line.", "Normal polling continues.", "Resetting and controlled restart sequence."),
        (1140, "GT-011", "production_restored", "PLC01", "INFO", "RECOVERY", "Production returns to steady operation with the changed timeout still loaded.", "Known communications only.", "Line rate recovers; jam_timeout_s remains 20."),
    ]
    return [dict(zip(GROUND_TRUTH_COLUMNS, [
        (start + timedelta(seconds=offset)).isoformat(), event_id, event_type, actor,
        config["asset_name"], severity, label, description, network_signal, process_signal,
    ])) for offset, event_id, event_type, actor, severity, label, description, network_signal, process_signal in events]


def data_dictionary() -> list[dict]:
    rows: list[dict] = []

    def add(dataset, column, data_type, unit, description, normal, incident):
        rows.append(dict(zip(DICTIONARY_COLUMNS, [dataset, column, data_type, unit, description, normal, incident])))

    process_definitions = {
        "timestamp": ("datetime", "UTC", "One-second telemetry timestamp."),
        "line_state": ("category", "", "PLC process state."),
        "conveyor_run": ("boolean", "", "Conveyor run command/state."),
        "safety_ok": ("boolean", "", "Synthetic safety-chain health; never altered by the incident."),
        "estop": ("boolean", "", "Emergency-stop state; always false in this scenario."),
        "jam_sensor": ("boolean", "", "Carton accumulation/jam input."),
        "fault_lamp": ("boolean", "", "PLC fault indication."),
        "fault_code": ("category", "", "PLC diagnostic code."),
        "jam_timeout_s": ("integer", "seconds", "Configured jam persistence before a fault."),
        "speed_setpoint_pct": ("number", "%", "Commanded conveyor speed."),
        "actual_speed_pct": ("number", "%", "Measured/simulated conveyor speed."),
        "motor_current_a": ("number", "A", "Drive motor current."),
        "vibration_mm_s": ("number", "mm/s", "Motor/gearbox vibration velocity."),
        "temperature_c": ("number", "deg C", "Drive/motor temperature."),
        "line_rate_ppm": ("number", "packages/min", "Packaging throughput."),
        "item_count": ("integer", "packages", "Cumulative processed count."),
        "reject_count": ("integer", "packages", "Cumulative reject count."),
        "reject_rate_pct": ("number", "%", "Instantaneous simulated reject rate."),
        "plc_cycle_ms": ("number", "ms", "PLC task-cycle duration."),
        "network_rx_kbps": ("number", "kbps", "PLC receive throughput."),
        "network_tx_kbps": ("number", "kbps", "PLC transmit throughput."),
        "ground_truth_label": ("category", "", "Known scenario phase used only for evaluation."),
    }
    for column, (data_type, unit, description) in process_definitions.items():
        add("process_telemetry", column, data_type, unit, description,
            "Stable production with planned stops and short non-tripping disturbances.",
            "Recon, download, timeout change, jam impact, delayed fault, and recovery are labelled.")

    network_descriptions = {
        "timestamp": "Network-session start time.", "src_ip": "Source host address.",
        "dst_ip": "Destination PLC address.", "src_port": "Source transport port.",
        "dst_port": "PLC destination port.", "proto": "Transport protocol.",
        "service": "Normalized service label.", "duration": "Session duration.",
        "orig_bytes": "Originator-to-PLC bytes.", "resp_bytes": "PLC-to-originator bytes.",
        "conn_state": "Zeek-style normalized connection outcome.",
        "suricata_alert": "Synthetic alert overlap indicator.",
        "programming_activity": "Ground-truth download-window indicator.",
    }
    for column, description in network_descriptions.items():
        add("network_sessions", column, "number" if column in {"src_port", "dst_port", "duration", "orig_bytes", "resp_bytes"} else "text", "", description,
            "Known HMI, historian, and sparse engineering sessions.",
            "New source, failed scan connections, and high-volume CODESYS download sessions.")

    for column in GROUND_TRUTH_COLUMNS:
        add("ground_truth", column, "text", "", "Incident timeline field.", "Not applicable.", "Documents the scenario and expected evidence.")
    return rows


def write_artifacts(root: Path) -> None:
    baseline = root / "artifacts" / "icspector" / "baseline"
    incident = root / "artifacts" / "icspector" / "incident"
    baseline.mkdir(parents=True, exist_ok=True)
    incident.mkdir(parents=True, exist_ok=True)
    (baseline / "conveyor_logic.st").write_text("VAR\n  Jam_Timeout : TIME := T#5s;\nEND_VAR\n", encoding="utf-8")
    (incident / "conveyor_logic.st").write_text("VAR\n  Jam_Timeout : TIME := T#20s;\nEND_VAR\n", encoding="utf-8")
    metadata = {"plc": "PLC01", "runtime": "CODESYS V3", "application": "PackagingLine", "source": "synthetic-realistic-demo"}
    (baseline / "metadata.json").write_text(json.dumps({**metadata, "snapshot": "baseline", "jam_timeout_s": 5}, indent=2), encoding="utf-8")
    (incident / "metadata.json").write_text(json.dumps({**metadata, "snapshot": "incident", "jam_timeout_s": 20}, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a realistic, deterministic packaging-line PLC dataset.")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()

    config = load_config(args.config)
    rng = random.Random(42)
    normal_start = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    incident_start = datetime(2026, 9, 1, 14, 0, tzinfo=timezone.utc)
    synthetic_dir = args.output_root / "data" / "synthetic"
    feature_dir = args.output_root / "data" / "features"

    normal_process = process_rows(config, rng, normal_start, 7_200, incident=False)
    incident_process = process_rows(config, rng, incident_start, 1_800, incident=True)
    normal_network = baseline_network(config, rng, normal_start, 7_200)
    incident_network_rows = incident_network(config, rng, incident_start, 1_800)
    truth = ground_truth(incident_start, config)
    dictionary = data_dictionary()

    write_csv(synthetic_dir / "packaging_line_process_normal.csv", PROCESS_COLUMNS, normal_process)
    write_csv(synthetic_dir / "packaging_line_process_incident.csv", PROCESS_COLUMNS, incident_process)
    write_csv(synthetic_dir / "packaging_line_network_normal.csv", SESSION_COLUMNS, normal_network)
    write_csv(synthetic_dir / "packaging_line_network_incident.csv", SESSION_COLUMNS, incident_network_rows)
    write_csv(synthetic_dir / "packaging_line_ground_truth.csv", GROUND_TRUTH_COLUMNS, truth)
    write_csv(synthetic_dir / "data_dictionary.csv", DICTIONARY_COLUMNS, dictionary)
    write_csv(feature_dir / "malcolm_normal_sessions.csv", SESSION_COLUMNS, normal_network)
    write_csv(feature_dir / "malcolm_incident_sessions.csv", SESSION_COLUMNS, incident_network_rows)
    write_artifacts(args.output_root)

    print(json.dumps({
        "normal_process_rows": len(normal_process),
        "incident_process_rows": len(incident_process),
        "normal_network_sessions": len(normal_network),
        "incident_network_sessions": len(incident_network_rows),
        "ground_truth_events": len(truth),
        "output_directory": str(synthetic_dir),
    }, indent=2))


if __name__ == "__main__":
    main()
