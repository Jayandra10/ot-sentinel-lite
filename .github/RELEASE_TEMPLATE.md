# Release vX.Y.Z - YYYY-MM-DD

## Summary

One-paragraph release summary describing what changed and why it matters.

## Highlights

- Highlight 1
- Highlight 2
- Highlight 3

## Added

- New capability or component

## Changed

- Behavioral or UX update

## Fixed

- Bug fix and impact

## Deprecated

- Any soon-to-be-removed functionality

## Removed

- Fully removed behavior, file, or workflow

## Security and safety notes

- Lab-only reminders, risk boundaries, and safety constraints.
- Any configuration changes relevant to secure operation.

## Data and model impact

- Feature contract changes: Yes or No
- Model behavior changes: Yes or No
- Risk score logic changes: Yes or No
- Migration required: Yes or No

## Dashboard impact

- Sections affected
- User-visible differences
- Any known limitations

## Breaking changes

- None

If breaking changes exist, list each one with migration guidance.

## Validation evidence

- Automated tests:
  - pytest: pass or fail
- Manual checks:
  - Dashboard review completed: Yes or No
  - Synthetic pipeline run completed: Yes or No

## Artifacts

- `sample_output/incident_summary.json`
- `sample_output/events.csv`
- `sample_output/scored_incident_windows.csv`
- Any additional outputs relevant to this release

## Upgrade notes

1. Pull latest changes.
2. Reinstall dependencies if requirements changed.
3. Re-run `python scripts/run_demo.py`.
4. Re-run `pytest -q`.
5. Launch `streamlit run dashboard/app.py`.

## Contributors

- @username

## Full changelog

Compare: https://github.com/Jayandra10/ot-sentinel-lite/compare/vPREV...vX.Y.Z
