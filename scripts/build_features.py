from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from common import REPO_ROOT, load_config, read_sessions


def build_windows(sessions: pd.DataFrame, config: dict) -> pd.DataFrame:
    plc_sessions = sessions.loc[sessions["dst_ip"] == config["plc_ip"]].copy()
    if plc_sessions.empty:
        raise ValueError(f"No sessions target PLC IP {config['plc_ip']}")

    window_seconds = int(config["window_seconds"])
    plc_sessions["window_start"] = plc_sessions["timestamp"].dt.floor(f"{window_seconds}s")
    plc_sessions["is_failed"] = ~plc_sessions["conn_state"].isin(
        config["normal_conn_states"]
    )
    plc_sessions["is_programming_port"] = plc_sessions["dst_port"].isin(
        config["programming_ports"]
    )

    windows = (
        plc_sessions.groupby(["window_start", "src_ip"], as_index=False)
        .agg(
            conn_count=("timestamp", "size"),
            unique_dst_ports=("dst_port", "nunique"),
            total_orig_bytes=("orig_bytes", "sum"),
            total_resp_bytes=("resp_bytes", "sum"),
            mean_duration=("duration", "mean"),
            failed_ratio=("is_failed", "mean"),
            programming_port_count=("is_programming_port", "sum"),
            suricata_alert=("suricata_alert", "max"),
            programming_activity=("programming_activity", "max"),
        )
        .sort_values(["window_start", "src_ip"])
    )
    windows["new_source"] = (~windows["src_ip"].isin(config["baseline_sources"])).astype(int)
    windows["asset"] = config["asset_name"]
    windows["window_start"] = windows["window_start"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return windows


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate Malcolm/Zeek sessions into windows.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    windows = build_windows(read_sessions(args.input), config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    windows.to_csv(args.output, index=False)
    print(f"Wrote {len(windows)} windows to {args.output}")


if __name__ == "__main__":
    main()
