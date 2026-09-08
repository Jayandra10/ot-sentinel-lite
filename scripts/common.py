from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "lab.example.json"

SESSION_COLUMNS = [
    "timestamp",
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "proto",
    "service",
    "duration",
    "orig_bytes",
    "resp_bytes",
    "conn_state",
    "suricata_alert",
    "programming_activity",
]

MODEL_FEATURES = [
    "conn_count",
    "unique_dst_ports",
    "total_orig_bytes",
    "total_resp_bytes",
    "mean_duration",
    "failed_ratio",
    "programming_port_count",
]


def load_config(path: str | Path | None = None) -> dict:
    config_path = Path(path) if path else DEFAULT_CONFIG
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    required = {
        "asset_name",
        "plc_ip",
        "baseline_sources",
        "programming_ports",
        "normal_conn_states",
        "window_seconds",
        "risk_points",
    }
    missing = sorted(required - config.keys())
    if missing:
        raise ValueError(f"Missing required configuration keys: {', '.join(missing)}")
    return config


def require_columns(frame: pd.DataFrame, columns: Iterable[str], source: Path) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{source} is missing columns: {', '.join(missing)}")


def read_sessions(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    frame = pd.read_csv(source)
    require_columns(frame, SESSION_COLUMNS, source)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
    for column in ("src_port", "dst_port", "duration", "orig_bytes", "resp_bytes"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    for column in ("suricata_alert", "programming_activity"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).astype(int)
    return frame


def severity_for_score(score: int | float) -> str:
    value = float(score)
    if value >= 80:
        return "CRITICAL"
    if value >= 60:
        return "HIGH"
    if value >= 30:
        return "MEDIUM"
    return "LOW"

