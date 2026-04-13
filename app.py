"""
Module: app
Version: 1.0.0
Description: AI-PMC Governance Server — main Flask application with CORS and all endpoints
"""

import os
import logging

from flask import Flask, send_from_directory
from flask_cors import CORS

from api.upload import upload_bp

logging.basicConfig(
    level=os.environ.get("SOVEREIGN_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static")
CORS(app)

# ── Blueprints ──────────────────────────────────────────────────────────────
app.register_blueprint(upload_bp)


# ── Health check ────────────────────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health_check():
    """Return service health status."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "AI-PMC Governance",
    }


# ── Frontend SPA fallback ───────────────────────────────────────────────────
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path: str):
    """Serve the React/Vanilla SPA; fall back to index.html for client-side routes."""
    if path and os.path.exists(os.path.join("static", path)):
        return send_from_directory("static", path)
    return send_from_directory("static", "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("SOVEREIGN_PORT", 8080))
    logger.info(f"Starting AI-PMC Governance server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
