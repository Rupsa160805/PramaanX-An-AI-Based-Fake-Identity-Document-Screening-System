# PramaanX P4 — biometric verification service

Standalone Flask microservice for webcam capture, live-face verification, and
the optional lightweight liveness check. It is designed to wrap the P3
`face_match.py`, `webcam_capture.py`, and `database.py` handoff when those
modules are on `PYTHONPATH`; local adapters keep the service runnable while
the rest of the project is being integrated.

## Run locally

```powershell
cd C:\path\to\pramaanx_p4
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r server\requirements.txt
$env:P4_FACE_THRESHOLD = "0.45"
python -m server.app
```

The service listens on `http://localhost:5001`.

## MongoDB Atlas

The merged repository supports the schema in the supplied Atlas specification:
`documents`, `verification_results`, `alerts`, `users`, `audit_logs`, and the
TTL-managed `captures` collection. On Atlas startup it creates the required
indexes and applies `$jsonSchema` validators for `documents` and
`verification_results` when the configured database user has permission to run
`collMod`.

Configure the application with environment variables, not source code:

```powershell
$env:P4_DATABASE_MODE = "mongo"
$env:MONGODB_URI = "mongodb+srv://<least-privilege-user>:<password>@<cluster>/<database>?retryWrites=true&w=majority"
$env:MONGODB_DATABASE = "pramaanx"
python -m server.app
```

`P4_DATABASE_MODE=auto` uses the local reference JSON when `MONGODB_URI` is
empty; if a URI is supplied but unreachable, the API reports a degraded
database state rather than silently writing to local data. Check
`GET /api/db/health` or `GET /api/v1/health` before a demo. The Atlas-backed
path has been verified with the configured project cluster; keep the URI in
the process environment and never commit it.

## Synthetic demo data

The repository includes clearly labeled, non-real upload fixtures under
`../demo_artifacts`. They are intended to exercise the complete frontend ->
Flask -> Atlas flow without using identity documents or claiming a legal
authenticity verdict.

With the Atlas environment variables set, seed the reference documents and a
development officer account once:

```powershell
python -m server.scripts.seed_demo_atlas
python -m server.app
```

The synthetic demo pipeline (`server.services.demo_document_pipeline`) is the
default when `P4_DOCUMENT_PIPELINE_MODULE` is unset, so the demo differentiates
the `demo_artifacts` images out of the box. It only recognizes the generated
synthetic markers and rejects any other image (returning `not_available`), so
real uploads never receive a fabricated result.

To run the **real** model instead of the marker demo, set
`P4_DOCUMENT_PIPELINE_MODULE=ai_pipeline.ai.pipeline`. That module runs EasyOCR
text/MRZ extraction and a fine-tuned ResNet18 tamper classifier on the actual
pixels. One-time setup from the repository root:

```powershell
pip install easyocr torch torchvision          # EasyOCR + PyTorch (CPU is fine)
python ai_pipeline/ai/ml/build_dataset.py       # build genuine/tampered dataset
python ai_pipeline/ai/ml/train.py               # -> ai_pipeline/ai/ml/tampering_model.pth
```

Then start Flask with the variable set:

```powershell
$env:P4_DOCUMENT_PIPELINE_MODULE = "ai_pipeline.ai.pipeline"
python -m server.app
```

The tampering verdict then comes from the trained network reading the image
(e.g. a clean demo document scores ~0.0002 tampered probability, an altered one
~0.97), and that score feeds both the risk score and the on-chain ANALYSIS (H2)
hash. The bundled dataset builder is procedurally generated for local
demonstration; retrain on a real labelled document corpus for production
accuracy.

The demo login is `demo.officer@pramaanx.local` / `Demo@12345`. Upload the
files in `demo_artifacts` from the Document screening page and enter the
document number shown in the filename. The fixture README records the
expected LOW, MEDIUM, and HIGH evidence outcomes. The synthetic pipeline is
only for local demonstration; configure the real OCR/MRZ/tampering module for
production or model evaluation.

The React operator console lives in `../frontend`. Build it from the
repository root with `npm install` and `npm run build` inside that directory;
Flask will then serve the generated console at `/`. For hot reload, run
`npm run dev` in `frontend` and keep Flask running on port 5001.

If starting from the repository root, use `python -m flask --app server.app:app run --port 5001`.

## Stable API contract

### `GET /api/health`

```json
{"status": "ok"}
```

### `POST /api/capture`

Request body is optional. Use `{ "preview": true }` for the kiosk flow.

```json
{
  "captured": true,
  "photo_path": "/tmp/pramaanx_captures/live_20260909_142300_000000.jpg",
  "error": null
}
```

### `POST /api/upload-photo`

Browser clients send a multipart form with a `photo` field. The response
returns a server-side path that can be passed to `/api/verify-face`:

```json
{
  "uploaded": true,
  "photo_path": "C:\\temp\\pramaanx_captures\\live_abc.jpg",
  "error": null
}
```

`POST /api/upload-frames` accepts repeated `frames` fields and returns a
`frame_paths` array for `/api/liveness-check` or `/api/verify-face`.

### `POST /api/verify-face`

```json
{
  "live_photo_path": "/tmp/pramaanx_captures/live.jpg",
  "document_number": "Q2714253",
  "frame_paths": ["/tmp/frames/1.jpg", "/tmp/frames/2.jpg"]
}
```

`frame_paths` is optional for backwards compatibility with the first P2
integration. Without it, `liveness_passed` is `true` and
`liveness_performed` is `false`; the response says that liveness was not
evaluated. Send either `frame_paths` or `video_clip_path` to evaluate it; a
failed motion check blocks the match.

The response always includes the stable fields:

```json
{
  "found_in_database": true,
  "similarity": 0.87,
  "is_match": true,
  "threshold_used": 0.45,
  "liveness_passed": true,
  "liveness_performed": true,
  "confidence_label": "HIGH",
  "reason": "similarity 0.870 is at or above calibrated threshold 0.450",
  "error": null
}
```

For an unknown record, similarity is `null`; the service never invents a
score. For no face, the service returns `error: "no face detected"` and a
reason. HTTP 200 is used for expected business outcomes such as an unknown
document or a liveness failure; malformed input is 400, unusable biometric
input is 422, and unavailable model/runtime dependencies are 503.

### `POST /api/liveness-check`

```json
{
  "frame_paths": ["/tmp/frames/1.jpg", "/tmp/frames/2.jpg", "/tmp/frames/3.jpg"]
}
```

This is a motion heuristic, not a production-grade anti-spoofing detector.
The same endpoint also accepts `{ "video_clip_path": "C:\\demo\\clip.mp4" }`.

### Merged document and operations API

- `POST /api/v1/verify` — multipart `document`, optional `document_number`; stores the result and creates a medium/high-risk alert.
- `GET /api/v1/dashboard` — counts and recent verification results.
- `GET /api/v1/history` — persisted screening history with `limit`, `skip`, and `search` query parameters.
- `GET /api/v1/alerts` — open or filtered alerts.
- `POST /api/v1/alerts/<id>/resolve` — append-only audit entry plus alert resolution.
- `GET /api/v1/health` and `GET /api/db/health` — service and repository status.

The React console uses these endpoints through the Vite `/api` proxy. The
original P4 biometric endpoints remain available at `/api/verify-face`,
`/api/capture`, `/api/upload-photo`, `/api/upload-frames`, and
`/api/liveness-check`.

## P3 integration

Put P3's modules on `PYTHONPATH`, or set:

```powershell
$env:P4_P3_FACE_MODULE = "path.to.face_match"
$env:P4_P3_DATABASE_MODULE = "path.to.database"
$env:P4_P3_WEBCAM_MODULE = "path.to.webcam_capture"
```

The P3 face adapter is preferred. Its `verify_against_database(live_path,
document_number)` result should include a 0–1 `similarity`, or a dict with an
`error`. The local fallback uses InsightFace `buffalo_l` and the configured
reference JSON store.

## Threshold calibration

For the utility's simple directory mode, put 5–10 photos of one person in
the `same` directory and one photo of each different person in the
`different` directory. Use the actual demo lighting:

```powershell
python server\scripts\calibrate_threshold.py `
  --same ..\calibration\same `
  --different ..\calibration\different `
  --output calibration_results.json
```

Measure the separation; do not assume the example `0.45` threshold is right
for the team's lighting and camera.

The utility skips a pair when a photo cannot be read or no face is detected,
then writes the pair and reason to `skipped_pairs`. A result is marked
`calibration_valid: false` and keeps `baseline_threshold` unless at least one
same-person and one different-person score were obtained. This prevents an
incomplete run from producing a misleading `0.0` threshold. The attached
sample evidence is preserved at
`server/demo_data/calibration_results_sample_run.json` and is
intentionally not a production calibration.

## Tests

```powershell
pytest -q
```

The default tests use injected fakes and do not require a camera or an
InsightFace model. The full-stack tests are opt-in:

```powershell
$env:P2_BASE_URL = "http://localhost:5000"
$env:P4_INTEGRATION_LIVE_PHOTO_PATH = "C:\demo\live.jpg"
pytest -q server\tests\integration_test.py
```

## Privacy and demo scope

The prototype is for synthetic/sample identity records and authorized team
photos. It is decision support, not an automatic fake/genuine determination,
and it is not connected to real government databases. Production deployment
would require explicit consent, encrypted biometric templates, retention and
delete controls, access auditing, legal authorization, and applicable data
protection compliance.
