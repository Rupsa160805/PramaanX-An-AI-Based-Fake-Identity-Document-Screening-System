from __future__ import annotations

from pathlib import Path

from flask import Blueprint, Response, abort, jsonify, send_from_directory

index_bp = Blueprint("index", __name__)
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


LANDING_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PramaanX P4 Biometric Service</title>
  <style>
    :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    body { margin: 0; background: #f4f7fb; color: #172033; }
    main { max-width: 940px; margin: 0 auto; padding: 56px 24px; }
    .hero, .card { background: #fff; border: 1px solid #dfe6f0; border-radius: 18px; box-shadow: 0 8px 30px #23395d12; }
    .hero { padding: 34px; background: linear-gradient(135deg, #102a43, #1f5d8f); color: #fff; }
    h1 { margin: 0 0 8px; font-size: clamp(2rem, 5vw, 3.4rem); letter-spacing: -0.04em; }
    .subtitle { margin: 0; color: #dbeafe; font-size: 1.08rem; }
    .status { display: inline-flex; align-items: center; gap: 8px; margin-top: 24px; padding: 8px 12px; border-radius: 999px; background: #ffffff1c; }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: #fbbf24; }
    .dot.ok { background: #34d399; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 16px; margin-top: 22px; }
    .card { padding: 22px; }
    .card h2 { margin: 0 0 10px; font-size: 1.05rem; }
    .card p { margin: 0; color: #526176; line-height: 1.55; }
    .endpoint { display: block; margin: 10px 0; font-family: ui-monospace, monospace; color: #0f4c81; }
    .note { margin-top: 22px; color: #526176; font-size: .92rem; }
    button { margin-top: 18px; border: 0; border-radius: 9px; padding: 10px 14px; background: #fff; color: #0f4c81; cursor: pointer; font-weight: 700; }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>PramaanX P4</h1>
      <p class="subtitle">Biometric verification, webcam capture, and liveness service</p>
      <div class="status"><span id="dot" class="dot"></span><span id="status">Checking service health…</span></div>
      <br><button type="button" onclick="checkHealth()">Check health</button>
    </section>
    <section class="grid">
      <article class="card"><h2>Face verification</h2><p class="endpoint">POST /api/verify-face</p><p>Matches a live photo against the reference photo for a document number and returns an explainable similarity result.</p></article>
      <article class="card"><h2>Webcam capture</h2><p class="endpoint">POST /api/capture</p><p>Captures a blind or preview-confirmed frame using the configured camera.</p></article>
      <article class="card"><h2>Liveness check</h2><p class="endpoint">POST /api/liveness-check</p><p>Checks motion across frames or a short video. This is an MVP heuristic, not production anti-spoofing.</p></article>
    </section>
    <p class="note">This prototype is decision support for an authorized officer. It uses synthetic/sample records and is not connected to government databases.</p>
  </main>
  <script>
    async function checkHealth() {
      const status = document.getElementById('status');
      const dot = document.getElementById('dot');
      status.textContent = 'Checking service health…';
      dot.classList.remove('ok');
      try {
        const response = await fetch('/api/health');
        const body = await response.json();
        if (!response.ok || body.status !== 'ok') throw new Error('unhealthy');
        status.textContent = 'Service online';
        dot.classList.add('ok');
      } catch (_) {
        status.textContent = 'Service health check failed';
      }
    }
    checkHealth();
  </script>
</body>
</html>"""


@index_bp.get("/")
def index():
    if (FRONTEND_DIST / "index.html").exists():
        return send_from_directory(FRONTEND_DIST, "index.html")
    return Response(LANDING_PAGE, mimetype="text/html")


@index_bp.get("/assets/<path:asset_path>")
def frontend_asset(asset_path):
    if not FRONTEND_DIST.exists():
        abort(404)
    return send_from_directory(FRONTEND_DIST / "assets", asset_path)


@index_bp.get("/<path:route_path>")
def frontend_route(route_path):
    # Let Flask's API routes remain authoritative if an unknown API path is
    # requested instead of returning the React document for it.
    if route_path.startswith("api/"):
        abort(404)
    if (FRONTEND_DIST / "index.html").exists():
        return send_from_directory(FRONTEND_DIST, "index.html")
    abort(404)


@index_bp.get("/api")
def api_index():
    return jsonify(
        {
            "service": "pramaanx-p4-biometric",
            "status": "ok",
            "endpoints": {
                "health": "/api/health",
                "capture": "/api/capture",
                "verify_face": "/api/verify-face",
                "liveness": "/api/liveness-check",
                "database_health": "/api/db/health",
                "document_verify": "/api/v1/verify",
                "dashboard": "/api/v1/dashboard",
                "history": "/api/v1/history",
                "alerts": "/api/v1/alerts",
            },
        }
    )
