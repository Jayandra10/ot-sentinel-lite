# Contributing

Thank you for improving OT Sentinel Lite.

## Scope and safety

- This project is for synthetic and isolated lab use only.
- Do not connect these workflows to production or third-party controllers.
- Do not commit secrets, proprietary PLC project files, or sensitive packet captures.

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies.
3. Run tests before creating a pull request.

PowerShell example:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pytest -q
```

## Development workflow

1. Create a topic branch from `main`.
2. Keep changes focused and small when possible.
3. Update documentation when behavior or contracts change.
4. Run `pytest -q` locally.
5. Open a pull request with a clear summary.

## Pull request checklist

- [ ] Tests pass locally.
- [ ] Documentation reflects the change.
- [ ] No generated outputs were committed unintentionally.
- [ ] Risk logic changes include rationale and validation evidence.
- [ ] Dashboard changes were visually checked.

## Coding notes

- Prefer deterministic data processing over hidden state.
- Preserve existing output contracts unless intentionally versioned.
- Add clear error messages when input contracts are violated.
