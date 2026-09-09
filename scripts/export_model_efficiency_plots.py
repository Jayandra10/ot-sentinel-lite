from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "plots"


def load_scores(path: Path, label: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if "anomaly_score" not in frame.columns:
        raise ValueError(f"Missing required column 'anomaly_score' in {path}")
    result = frame.copy()
    result["anomaly_score"] = pd.to_numeric(result["anomaly_score"], errors="coerce")
    result = result.dropna(subset=["anomaly_score"])
    result["class"] = label
    return result


def load_threshold(config_path: Path, fallback: float = 75.0) -> float:
    if not config_path.exists():
        return fallback
    config = json.loads(config_path.read_text(encoding="utf-8"))
    try:
        return float(config.get("anomaly_threshold", fallback))
    except (TypeError, ValueError):
        return fallback


def threshold_curves(normal_scores: np.ndarray, incident_scores: np.ndarray) -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    for threshold in np.arange(0.0, 101.0, 1.0):
        fp_rate = float((normal_scores >= threshold).mean())
        tp_rate = float((incident_scores >= threshold).mean())

        tp = float((incident_scores >= threshold).sum())
        fp = float((normal_scores >= threshold).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp_rate
        f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

        rows.append(
            {
                "threshold": threshold,
                "false_alert_rate": fp_rate,
                "detection_rate": tp_rate,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )
    return pd.DataFrame(rows)


def nearest_threshold_row(curves: pd.DataFrame, threshold: float) -> pd.Series:
    threshold_index = (curves["threshold"] - threshold).abs().idxmin()
    return curves.loc[threshold_index]


def style_axis(ax: plt.Axes) -> None:
    ax.grid(True, color="#dbe3ef", linewidth=0.8, alpha=0.8)
    ax.set_facecolor("#f8fafc")


def save_distribution_plot(
    normal_scores: np.ndarray,
    incident_scores: np.ndarray,
    threshold: float,
    output_path: Path,
) -> None:
    bins = np.arange(0, 102, 2)
    fig, ax = plt.subplots(figsize=(10.5, 5.5), dpi=180)

    ax.hist(
        normal_scores,
        bins=bins,
        alpha=0.65,
        density=True,
        color="#3b82f6",
        edgecolor="#1e3a8a",
        linewidth=0.4,
        label=f"Normal windows (n={len(normal_scores)})",
    )
    ax.hist(
        incident_scores,
        bins=bins,
        alpha=0.55,
        density=True,
        color="#ef4444",
        edgecolor="#7f1d1d",
        linewidth=0.4,
        label=f"Incident windows (n={len(incident_scores)})",
    )
    ax.axvline(
        threshold,
        color="#f59e0b",
        linestyle="--",
        linewidth=2.0,
        label=f"Configured threshold ({threshold:.0f})",
    )

    ax.set_title("Anomaly score distribution: normal vs incident")
    ax.set_xlabel("Calibrated anomaly score")
    ax.set_ylabel("Density")
    style_axis(ax)
    ax.legend(frameon=True, facecolor="white", edgecolor="#cbd5e1")
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def save_threshold_curve_plot(curves: pd.DataFrame, threshold: float, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 5.5), dpi=180)

    ax.plot(
        curves["threshold"],
        100.0 * curves["false_alert_rate"],
        color="#2563eb",
        linewidth=2.3,
        label="False alert rate on normal windows",
    )
    ax.plot(
        curves["threshold"],
        100.0 * curves["detection_rate"],
        color="#dc2626",
        linewidth=2.3,
        label="Detection rate on incident windows",
    )
    ax.plot(
        curves["threshold"],
        100.0 * curves["precision"],
        color="#0f766e",
        linewidth=2.0,
        linestyle=":",
        label="Precision at threshold",
    )

    threshold_row = nearest_threshold_row(curves, threshold)
    x = float(threshold_row["threshold"])
    y_false = 100.0 * float(threshold_row["false_alert_rate"])
    y_detect = 100.0 * float(threshold_row["detection_rate"])
    ax.scatter([x], [y_false], color="#2563eb", s=36, zorder=5)
    ax.scatter([x], [y_detect], color="#dc2626", s=36, zorder=5)

    best_f1_idx = curves["f1"].idxmax()
    best_f1 = curves.loc[best_f1_idx]
    ax.axvline(
        float(best_f1["threshold"]),
        color="#6d28d9",
        linestyle="-.",
        linewidth=1.8,
        label=f"Best F1 threshold ({best_f1['threshold']:.0f})",
    )

    ax.axvline(
        threshold,
        color="#f59e0b",
        linestyle="--",
        linewidth=1.8,
        label=f"Configured threshold ({threshold:.0f})",
    )

    ax.set_title("Threshold efficiency trade-offs")
    ax.set_xlabel("Anomaly score threshold")
    ax.set_ylabel("Rate (%)")
    ax.set_ylim(0, 105)
    style_axis(ax)
    ax.legend(frameon=True, facecolor="white", edgecolor="#cbd5e1")
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def save_roc_proxy_plot(curves: pd.DataFrame, threshold: float, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 6.2), dpi=180)

    x = curves["false_alert_rate"].to_numpy()
    y = curves["detection_rate"].to_numpy()
    order = np.argsort(x)
    x_sorted = x[order]
    y_sorted = y[order]

    ax.plot(x_sorted, y_sorted, color="#7c3aed", linewidth=2.4, label="Threshold sweep")
    ax.plot([0, 1], [0, 1], color="#94a3b8", linestyle="--", linewidth=1.4, label="Random baseline")

    threshold_row = nearest_threshold_row(curves, threshold)
    x0 = float(threshold_row["false_alert_rate"])
    y0 = float(threshold_row["detection_rate"])
    ax.scatter([x0], [y0], color="#f59e0b", s=52, zorder=5)
    ax.annotate(
        f"Configured threshold {threshold:.0f}",
        xy=(x0, y0),
        xytext=(10, -12),
        textcoords="offset points",
        fontsize=9,
        color="#78350f",
    )

    auc_proxy = float(np.trapezoid(y_sorted, x_sorted))
    ax.set_title(f"ROC-style trade-off curve (AUC ~ {auc_proxy:.3f})")
    ax.set_xlabel("False positive rate on normal windows")
    ax.set_ylabel("Detection rate on incident windows")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    style_axis(ax)
    ax.legend(frameon=True, facecolor="white", edgecolor="#cbd5e1", loc="lower right")
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export model efficiency plots to docs/plots")
    parser.add_argument(
        "--normal",
        type=Path,
        default=REPO_ROOT / "sample_output" / "scored_normal_windows.csv",
        help="Path to scored normal windows CSV",
    )
    parser.add_argument(
        "--incident",
        type=Path,
        default=REPO_ROOT / "sample_output" / "scored_incident_windows.csv",
        help="Path to scored incident windows CSV",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=REPO_ROOT / "config" / "lab.example.json",
        help="Path to config JSON containing anomaly_threshold",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where PNG plots will be written",
    )
    args = parser.parse_args()

    if not args.normal.exists() or not args.incident.exists():
        missing = [str(path) for path in (args.normal, args.incident) if not path.exists()]
        raise FileNotFoundError(
            "Missing scored window files. Run `python scripts/run_demo.py` first. Missing: "
            + ", ".join(missing)
        )

    normal = load_scores(args.normal, "normal")
    incident = load_scores(args.incident, "incident")

    normal_scores = normal["anomaly_score"].to_numpy(dtype=float)
    incident_scores = incident["anomaly_score"].to_numpy(dtype=float)
    threshold = load_threshold(args.config)
    curves = threshold_curves(normal_scores, incident_scores)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    distribution_plot = args.output_dir / "model_efficiency_distribution.png"
    threshold_plot = args.output_dir / "model_efficiency_threshold_curves.png"
    roc_plot = args.output_dir / "model_efficiency_roc_proxy.png"

    save_distribution_plot(normal_scores, incident_scores, threshold, distribution_plot)
    save_threshold_curve_plot(curves, threshold, threshold_plot)
    save_roc_proxy_plot(curves, threshold, roc_plot)

    summary_path = args.output_dir / "model_efficiency_summary.json"
    threshold_row = nearest_threshold_row(curves, threshold)
    summary = {
        "configured_threshold": threshold,
        "normal_windows": int(len(normal_scores)),
        "incident_windows": int(len(incident_scores)),
        "false_alert_rate_at_threshold": float(threshold_row["false_alert_rate"]),
        "detection_rate_at_threshold": float(threshold_row["detection_rate"]),
        "best_f1_threshold": float(curves.loc[curves["f1"].idxmax(), "threshold"]),
        "best_f1": float(curves["f1"].max()),
        "plots": [
            distribution_plot.relative_to(REPO_ROOT).as_posix(),
            threshold_plot.relative_to(REPO_ROOT).as_posix(),
            roc_plot.relative_to(REPO_ROOT).as_posix(),
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
