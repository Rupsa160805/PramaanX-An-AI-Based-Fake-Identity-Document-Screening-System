# PramaanX P4

Biometric verification and liveness microservice for the PramaanX prototype.

See [p4_biometric_service/README.md](p4_biometric_service/README.md) for the
backend API, P3 integration, threshold calibration, testing, and demo steps.

Quick start from this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r p4_biometric_service\requirements.txt
Push-Location frontend
npm install
npm run build
Pop-Location
python -m p4_biometric_service.app
```

The Flask service serves the built React operator console at
`http://127.0.0.1:5001/`. For frontend-only development, run `npm run dev` in
`frontend`; Vite proxies API calls to Flask.

The merged console also exposes document screening, Atlas-backed dashboard
metrics, screening history, open alerts, and the original P4 biometric flow.
Use `P4_DATABASE_MODE=local` for the offline JSON demo or set `MONGODB_URI`
and `MONGODB_DATABASE` to use MongoDB Atlas. Never commit the Atlas URI.

Synthetic upload fixtures and Atlas seed instructions are in
[demo_artifacts/README.md](demo_artifacts/README.md) and the backend
[README](p4_biometric_service/README.md#synthetic-demo-data). They are for
local testing only and are not real identity documents.

Run the local test suite with:

```powershell
python -m pytest -q
```

Threshold calibration skips unreadable/no-face pairs and records them in
`skipped_pairs`. It only selects a new threshold when both same-person and
different-person scores are available; otherwise it keeps the safe baseline
(`0.45`).
