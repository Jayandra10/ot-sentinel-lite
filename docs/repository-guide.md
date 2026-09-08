# Repository guide

This guide maps each top-level folder to its role in the project.

## Top-level map

| Path | Role |
|---|---|
| `config/` | Lab assumptions, thresholds, and weighted evidence configuration |
| `scripts/` | Data generation, feature extraction, artifact diff, and evidence correlation |
| `model/` | Isolation Forest training and scoring logic |
| `dashboard/` | Streamlit dashboard application |
| `data/synthetic/` | Synthetic process, network, and ground-truth source data |
| `data/features/` | Engineered model-ready feature windows |
| `artifacts/icspector/` | Baseline and incident PLC snapshot artifacts and manifests |
| `sample_output/` | Generated scoring, summary, and event outputs |
| `docs/` | Project documentation and operational runbooks |
| `tests/` | End-to-end regression checks |

## Core scripts and responsibilities

| File | Responsibility |
|---|---|
| `scripts/run_demo.py` | One-command orchestration for synthetic dataset to dashboard-ready outputs |
| `scripts/generate_sample_data.py` | Generates reproducible synthetic process and network incident scenario |
| `scripts/build_features.py` | Builds 60-second, source-scoped feature windows from sessions |
| `model/train_isolation_forest.py` | Trains on normal windows and scores incident windows |
| `scripts/icspector_manifest.py` | Computes hash manifests and artifact deltas |
| `scripts/correlate_events.py` | Produces explainable weighted event and incident summary |
| `dashboard/app.py` | Displays outcomes through risk, timeline, trigger, and audit panels |

## Data flow landmarks

- Feature inputs: `data/features/malcolm_normal_sessions.csv`, `data/features/malcolm_incident_sessions.csv`
- Model outputs: `sample_output/scored_incident_windows.csv`, `sample_output/model_metrics.json`
- Correlation outputs: `sample_output/events.csv`, `sample_output/incident_summary.json`
- Dashboard inputs: all `sample_output/*` plus process incident telemetry

## Testing and verification

- Main test: `tests/test_demo_pipeline.py`
- Test behavior: runs full synthetic pipeline in a temporary output root and validates data shape, safety constraints, and incident verdict consistency.
