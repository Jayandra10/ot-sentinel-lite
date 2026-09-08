# Demo runbook

1. Reset the PLC to the saved baseline and confirm `Jam_Timeout = T#5s`.
2. Start the ground-truth log and packet capture using synchronized clocks.
3. Demonstrate normal conveyor state changes from the CODESYS watch table.
4. Generate only the approved lab connection pattern, if the rogue VM is in scope.
5. Change `Jam_Timeout` to `T#20s`, download, and record the timestamp.
6. Stop capture after the post-change observation period.
7. Ingest/export network sessions and collect the post-change ICSpector snapshot.
8. Rebuild feature windows, retrain on normal only, compare artifacts, and correlate events.
9. Launch the dashboard and narrate the sources separately: Malcolm for network context, Isolation Forest for prioritization, ICSpector-derived artifacts for the PLC change, and deterministic rules for the final risk score.
10. Reset the PLC and archive only sanitized, shareable evidence.

