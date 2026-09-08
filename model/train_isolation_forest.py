from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from common import MODEL_FEATURES, require_columns  # noqa: E402


def calibrated_anomaly_score(
    decision_values: np.ndarray, normal_median: float, normal_p05: float
) -> np.ndarray:
    """Map lower Isolation Forest decisions to an interpretable 0-100 scale.

    The normal median maps near 10 and the fifth percentile maps near 60. Values
    more anomalous than the training tail rise toward 100. Calibration uses only
    the normal training distribution, so incident data cannot influence the scale.
    """

    spread = max(normal_median - normal_p05, 1e-9)
    scores = 10.0 + 50.0 * (normal_median - decision_values) / spread
    return np.clip(scores, 0.0, 100.0)


def score_frame(
    frame: pd.DataFrame,
    scaler: StandardScaler,
    model: IsolationForest,
    normal_median: float,
    normal_p05: float,
) -> pd.DataFrame:
    scored = frame.copy()
    transformed = scaler.transform(scored[MODEL_FEATURES])
    decisions = model.decision_function(transformed)
    scored["model_decision"] = decisions
    scored["anomaly_score"] = calibrated_anomaly_score(
        decisions, normal_median, normal_p05
    ).round(2)
    return scored


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the normal-only Isolation Forest.")
    parser.add_argument("--normal", type=Path, required=True)
    parser.add_argument("--incident", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "model")
    parser.add_argument(
        "--scored-output-dir", type=Path, default=REPO_ROOT / "sample_output"
    )
    args = parser.parse_args()

    normal = pd.read_csv(args.normal)
    incident = pd.read_csv(args.incident)
    require_columns(normal, MODEL_FEATURES, args.normal)
    require_columns(incident, MODEL_FEATURES, args.incident)
    if len(normal) < 10:
        raise ValueError("At least 10 normal windows are required for this demo model.")

    scaler = StandardScaler()
    normal_scaled = scaler.fit_transform(normal[MODEL_FEATURES])
    model = IsolationForest(
        n_estimators=200,
        contamination=0.02,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(normal_scaled)

    training_decisions = model.decision_function(normal_scaled)
    normal_median = float(np.median(training_decisions))
    normal_p05 = float(np.quantile(training_decisions, 0.05))
    scored_normal = score_frame(normal, scaler, model, normal_median, normal_p05)
    scored_incident = score_frame(incident, scaler, model, normal_median, normal_p05)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.scored_output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, args.output_dir / "model.joblib")
    joblib.dump(scaler, args.output_dir / "scaler.joblib")
    scored_normal.to_csv(args.scored_output_dir / "scored_normal_windows.csv", index=False)
    scored_incident.to_csv(
        args.scored_output_dir / "scored_incident_windows.csv", index=False
    )

    metrics = {
        "normal_windows": int(len(scored_normal)),
        "incident_windows": int(len(scored_incident)),
        "normal_anomaly_p95": float(scored_normal["anomaly_score"].quantile(0.95)),
        "normal_anomaly_max": float(scored_normal["anomaly_score"].max()),
        "normal_alert_rate_at_75": float(
            (scored_normal["anomaly_score"] >= 75).mean()
        ),
        "incident_anomaly_max": float(scored_incident["anomaly_score"].max()),
        "incident_windows_at_or_above_75": int(
            (scored_incident["anomaly_score"] >= 75).sum()
        ),
        "normal_decision_median": normal_median,
        "normal_decision_p05": normal_p05,
        "features": MODEL_FEATURES,
        "note": (
            "new_source is intentionally evaluated by the deterministic risk engine; "
            "a normal-only model cannot learn a useful split from a feature that is "
            "constant throughout training."
        ),
    }
    (args.scored_output_dir / "model_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
