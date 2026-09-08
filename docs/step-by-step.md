# OT Sentinel Lite: build sequence

This sequence separates safe local software work from hardware-dependent OT lab work. Do not connect the test tools to production, employer, campus, or third-party controllers.

## Checkpoint 0 - prove the software pipeline

Goal: demonstrate that the repository can generate realistic packaging-line telemetry and network sessions, create windows, train a normal-only model, compare two artifact snapshots, correlate evidence, and load the dashboard. A Raspberry Pi is not required for this checkpoint.

1. Create and activate a Python 3.11 virtual environment.
2. Install `requirements.txt`.
3. Run `python scripts/run_demo.py`.
4. Confirm `sample_output/incident_summary.json` reports `CRITICAL` and a risk score of `100` for the deliberately obvious synthetic incident.
5. Run `pytest -q`.
6. Launch `streamlit run dashboard/app.py` and inspect all five panels.

Exit criterion: the test passes and the dashboard renders. This checkpoint is independent of CODESYS, Malcolm, ICSpector, and packet capture.

Before continuing, review the generated workbook and ground-truth timeline. The normal and incident data should be understandable without relying on the anomaly score: process speed and throughput fall during the jam, motor current and vibration rise, the five-second baseline trip is missed, and the twenty-second configured timeout produces the delayed fault.

## Checkpoint 1 - isolate the lab network

Goal: place only the Windows engineering workstation and Raspberry Pi on a private lab-only segment.

1. Use a dedicated switch, dedicated VLAN, or host-only virtual network. Ethernet is preferred.
2. Start with Windows `192.168.50.10/24` and the Raspberry Pi `192.168.50.20/24`.
3. Confirm the lab interface is not bridged or routed to a production/corporate control network.
4. Verify bidirectional reachability with ping.
5. Record the Windows capture-interface name and MAC/IP mapping.

Exit criterion: Windows and Pi can communicate, and no unrelated controller is reachable from the lab segment.

## Checkpoint 2 - deploy the baseline CODESYS project

Goal: run the conveyor logic on the Pi soft PLC without physical I/O.

1. Install the current CODESYS Development System and the current Raspberry Pi SL package through the CODESYS Installer/Store.
2. Create the Raspberry Pi target and a cyclic task at 50-100 ms.
3. Add the variables and logic in `plc/conveyor_logic.st` to a POU.
4. Use a watch table to simulate Start, Stop, Photoeye, and Jam_Sensor.
5. Download, enter RUN, and exercise the watch-table sequence for at least 10 minutes.
6. Save the project as `BASELINE_v1` outside Git if the file contains licensed or proprietary material.
7. Capture the actual CODESYS ports used in this lab; update `config/lab.example.json` only after observing them.

Exit criterion: the counter increments on Photoeye edges, the jam timer sets Fault_Lamp after five seconds, and Wireshark sees the engineering-to-PLC session.

## Checkpoint 3 - capture normal and incident evidence

Goal: produce two repeatable, labelled captures.

1. Record 15-20 minutes of ordinary engineering and watch-table activity as `NORMAL_conveyor_baseline.pcapng`.
2. Maintain a ground-truth log with UTC timestamps, actor, action, and label.
3. Begin the incident capture with normal traffic already present.
4. On this isolated lab only, optionally use the dedicated rogue VM to make a narrow connection check to the PLC ports you already observed.
5. Change only `Jam_Timeout` from `T#5s` to `T#20s`, download, and record the exact timestamp.
6. Continue for 3-5 minutes and stop the capture.

Exit criterion: the incident capture contains ordinary traffic, the distinct lab source if used, the program download, and post-change traffic.

## Checkpoint 4 - process the PCAPs with Malcolm

Goal: export the minimum session fields consumed by `build_features.py`.

1. Use the official Ubuntu 24.04 quick start on a machine with adequate resources.
2. Complete Malcolm host tuning, configuration, and authentication before pulling images.
3. Upload the normal PCAP first, then the incident PCAP, with clear filename tags.
4. Filter by the PLC IP in OpenSearch Dashboards and Arkime.
5. Export session data with the columns documented in `README.md`.
6. Map exported column names to the repository data contract and set `programming_activity=1` only for the lab-labelled download window.

Exit criterion: the two session CSV files build clean feature windows with `scripts/build_features.py`.

## Checkpoint 5 - collect and compare ICSpector snapshots

Goal: make the PLC change evidence reproducible without overstating analyzer support.

1. Install ICSpector from Microsoft's repository and inspect the current CLI/plugin help.
2. Confirm the exact CODESYS V3 plugin token and port from the checked-out version; do not guess it.
3. Extract the baseline snapshot to `artifacts/icspector/baseline/`.
4. After the lab download, run the identical extraction into `artifacts/icspector/incident/`.
5. Run `scripts/icspector_manifest.py` to hash and compare what ICSpector actually exported.

Exit criterion: the event JSON reports the added, removed, or modified artifact paths. Phrase the finding as a changed ICSpector-derived snapshot unless an analyzer produced a more specific finding.

## Checkpoint 6 - replace synthetic evidence and rerun

1. Back up the synthetic outputs if you want to keep them.
2. Replace the session CSVs with sanitized Malcolm/Zeek exports that match the data contract.
3. Replace the two synthetic artifact directories with ICSpector exports.
4. Run the feature, model, manifest, and correlation commands from `README.md`.
5. Confirm the incident's maximum anomaly score exceeds the normal tail and review every risk reason.
6. Launch the dashboard, capture screenshots, and follow the demo runbook.

Exit criterion: every claim on the dashboard can be traced to a packet/session field, a model score, or a hashed PLC artifact.
