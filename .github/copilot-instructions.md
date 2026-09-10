# Repository Instructions

## Scope

- Keep all edits inside this repository unless explicitly requested.
- Treat this project as lab-only and synthetic-first.

## Safety and data handling

- Do not include credentials, access tokens, private captures, or proprietary controller files in commits.
- Do not introduce instructions that target production or third-party control systems.
- Preserve the synthetic scenario boundaries where safety indicators remain healthy and emergency stop remains inactive.

## Engineering expectations

- Keep changes small and reviewable.
- Preserve deterministic behavior for generated synthetic data.
- If data contracts, thresholds, feature definitions, or scoring rules change, update tests and documentation together.
- Prefer UTC timestamp handling across generated outputs and correlations.

## Verification

- Run the pipeline and tests after meaningful changes.
- Ensure dashboard and documentation remain consistent with generated outputs.

## Documentation standards

- Keep architecture and workflow documents aligned with implementation.
- Record model and evidence assumptions clearly when terminology changes.
