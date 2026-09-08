# Raspberry Pi integration plan

The Raspberry Pi is intentionally deferred until the synthetic pipeline is stable. This prevents hardware, licensing, networking, and packet-capture issues from obscuring problems in feature engineering, model scoring, correlation, or the dashboard.

## What the synthetic phase proves

1. The data contracts are usable for PLC process telemetry, OT network sessions, and a ground-truth log.
2. Normal-only Isolation Forest training produces reproducible scores.
3. A PLC artifact change can be hashed and correlated with network and process evidence.
4. The dashboard explains the incident without controlling a PLC.
5. Automated tests protect the pipeline before hardware is introduced.

## Replacement map

| Synthetic input | Raspberry Pi / lab replacement | Acceptance check |
|---|---|---|
| `packaging_line_process_*.csv` | Timestamped CODESYS watch export, OPC UA polling, or a purpose-built tag logger | Required tag names, UTC timestamps, units, and one-second cadence are preserved or mapped explicitly |
| `packaging_line_network_*.csv` | Sanitized Malcolm/Zeek session export from lab PCAPs | Session CSV satisfies the contract in `README.md` and produces non-empty 60-second windows |
| `artifacts/icspector/baseline/` | ICSpector export before the controlled PLC change | Manifest is reproducible and stored outside proprietary source files |
| `artifacts/icspector/incident/` | Identical ICSpector export after changing `Jam_Timeout` | Diff reports the expected changed artifact and no unexplained files |
| `packaging_line_ground_truth.csv` | UTC lab run log maintained by the operator | Every scan, download, parameter change, jam, reset, and recovery has an independently recorded timestamp |

## Pi readiness gates

Proceed to the Pi only when all of these are true:

- `python scripts/run_demo.py` completes.
- `pytest -q` passes.
- The workbook shows 7,200 normal process rows, 1,800 incident process rows, 1,928 normal sessions, 586 incident sessions, and 11 ground-truth events.
- The incident summary is `CRITICAL` with all expected reasons present.
- The lab network can be isolated from production, employer, campus, and third-party controllers.

## First Pi session

1. Place only the Windows engineering workstation and Pi on the private `192.168.50.0/24` lab segment.
2. Deploy the baseline conveyor logic with simulated I/O; do not connect physical machinery.
3. Confirm `Jam_Timeout = T#5s`, the jam fault trips after five seconds, and the safety chain remains separate from the exercise.
4. Capture at least 15 minutes of ordinary traffic and process tags as the normal baseline.
5. In a labelled incident run, change only `Jam_Timeout` to `T#20s`, download once, create one simulated jam, and record UTC timestamps.
6. Export the PCAP/session data, process tags, and baseline/incident ICSpector snapshots.
7. Map those files to the repository contracts, rerun the pipeline, and compare the results with the synthetic reference.

The Pi phase should replace evidence sources, not change the risk logic at the same time. Any mapping or threshold change should be reviewed separately so that regressions remain attributable.
