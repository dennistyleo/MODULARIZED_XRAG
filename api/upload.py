"""
Module: upload
Version: 1.0.0
Description: Upload API for AI-PMC Governance — handles file upload, RAG extraction, and axiom storage
"""

import os
import uuid
import json
import time
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from modules.rag_extractor import extract_axioms_from_pdf, extract_axioms_from_text

logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__)

# Configuration
UPLOAD_FOLDER = os.environ.get("SOVEREIGN_UPLOAD_FOLDER", "/tmp/axiom_uploads")
ALLOWED_EXTENSIONS = {
    "pdf", "txt", "md", "tex", "json", "csv", "xlsx",
    "png", "jpg", "jpeg", "tiff", "bmp", "webp",
    "wav", "mp3", "flac", "aac",
    "mp4", "avi", "mov", "mkv", "webm",
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename: str) -> bool:
    """Check if the file extension is in the allowed set."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@upload_bp.route("/api/upload", methods=["POST"])
def upload_file():
    """
    Handle file upload and RAG extraction.

    Request form data:
        file   — The uploaded file (multipart)
        engine — DEDUCTION | INDUCTION | ABDUCTION  (default: ABDUCTION)
        domain — Optional domain filter             (default: all)

    Response JSON:
        {
            "success": true,
            "run_id": "<uuid>",
            "axioms": [...],
            "axiom_count": N,
            "engine": "ABDUCTION",
            "extraction_time_ms": 1234
        }

    Error codes:
        E001 — File not found / unreadable
        E003 — Unexpected server error
    """
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided",
                        "error_code": "E001"}), 400

    file = request.files["file"]
    engine = request.form.get("engine", "ABDUCTION")
    domain = request.form.get("domain", "all")

    if file.filename == "":
        return jsonify({"success": False, "error": "Empty filename",
                        "error_code": "E001"}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "success": False,
            "error": f"File type not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            "error_code": "E001",
        }), 400

    run_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"

    filename = secure_filename(file.filename)
    safe_filename = f"{run_id}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, safe_filename)
    file.save(filepath)

    try:
        start_time = time.time()

        ext = filename.rsplit(".", 1)[-1].lower()

        if ext == "pdf":
            axioms = extract_axioms_from_pdf(filepath, engine)

        elif ext in {"txt", "md", "tex"}:
            with open(filepath, "r", encoding="utf-8") as fh:
                text = fh.read()
            axioms = extract_axioms_from_text(text, engine)

        elif ext == "json":
            with open(filepath, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, list):
                axioms = data
            elif isinstance(data, dict) and "axioms" in data:
                axioms = data["axioms"]
            else:
                axioms = []

        else:
            # Images / audio / video — placeholder pending multimodal pipeline
            axioms = [{
                "axiom_id": f"MEDIA_{run_id[:8].upper()}",
                "name": f"Media file: {filename}",
                "expression_latex": r"\text{Media analysis pending}",
                "domain": "multimodal",
                "status": "HYPOTHESIZED",
                "confidence": 0.5,
                "media_type": ext,
            }]

        extraction_time_ms = int((time.time() - start_time) * 1000)

        result = {
            "run_id": run_id,
            "timestamp": timestamp,
            "engine": engine,
            "domain": domain,
            "filename": filename,
            "extraction_time_ms": extraction_time_ms,
            "axioms": axioms,
            "axiom_count": len(axioms),
        }

        result_path = os.path.join(UPLOAD_FOLDER, f"{run_id}_result.json")
        with open(result_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)

        logger.info(
            f"upload: run_id={run_id} engine={engine} axioms={len(axioms)} "
            f"elapsed_ms={extraction_time_ms}"
        )

        return jsonify({
            "success": True,
            "run_id": run_id,
            "axioms": axioms,
            "axiom_count": len(axioms),
            "engine": engine,
            "extraction_time_ms": extraction_time_ms,
        })

    except Exception as exc:
        logger.error(f"E003: upload failed run_id={run_id} — {exc}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(exc),
            "error_code": "E003",
            "run_id": run_id,
        }), 500

    finally:
        # Temp file is intentionally retained for auditability; remove if storage is a concern.
        pass


@upload_bp.route("/api/upload/status/<run_id>", methods=["GET"])
def get_extraction_status(run_id: str):
    """
    Retrieve the result of a previous extraction by run ID.

    Args:
        run_id: UUID returned from the upload endpoint.

    Returns:
        {
            "success": true,
            "result": { ...full extraction result... }
        }

    Error codes:
        E001 — Run ID not found on disk
    """
    result_path = os.path.join(UPLOAD_FOLDER, f"{run_id}_result.json")

    if not os.path.exists(result_path):
        return jsonify({
            "success": False,
            "error": "Run ID not found",
            "error_code": "E001",
        }), 404

    try:
        with open(result_path, "r", encoding="utf-8") as fh:
            result = json.load(fh)
        return jsonify({"success": True, "result": result})
    except Exception as exc:
        logger.error(f"E003: status read failed run_id={run_id} — {exc}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(exc),
            "error_code": "E003",
        }), 500

# ============================================================
# SOFTWARE DEBUGGING ENDPOINT
# ============================================================

from modules.software_debugger import SoftwareDebugger

@upload_bp.route('/api/debug/software', methods=['POST'])
def debug_software():
    """Upload and debug software code (Python, JS, Verilog)"""
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    
    # Determine language from extension
    ext = file.filename.split('.')[-1].lower()
    lang_map = {
        'py': 'python',
        'js': 'javascript',
        'v': 'verilog',
        'sv': 'verilog',
        'json': 'json',
        'csv': 'csv'
    }
    language = lang_map.get(ext, 'unknown')
    
    if language == 'unknown':
        return jsonify({"error": f"Unsupported file type: {ext}"}), 400
    
    # Save temporarily
    temp_path = f"/tmp/{file.filename}"
    file.save(temp_path)
    
    # Run L1-L5 pipeline
    debugger = SoftwareDebugger()
    results = debugger.debug_file(temp_path, language)
    
    # Clean up
    os.remove(temp_path)
    
    return jsonify(results)

@upload_bp.route('/api/debug/software/auto-fix', methods=['POST'])
def auto_fix_software():
    """Auto-fix detected issues in software code"""
    
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    # Run debugger to get fixes
    temp_path = f"/tmp/{file.filename}"
    file.save(temp_path)
    
    debugger = SoftwareDebugger()
    results = debugger.debug_file(temp_path)
    
    # Generate fixed code based on suggestions
    fixed_code = None
    if results['fixes']:
        with open(temp_path, 'r') as f:
            original_code = f.read()
        
        fixed_code = original_code
        for fix in results['fixes']:
            # Apply each fix suggestion
            if fix['suggestion'] == '=== watching':
                fixed_code = fixed_code.replace('==', '===')
            elif fix['suggestion'] == 'except Exception as e:':
                fixed_code = fixed_code.replace('except:', 'except Exception as e:')
    
    os.remove(temp_path)
    
    return jsonify({
        "original_file": file.filename,
        "bugs_found": len(results['bugs']),
        "score": results['score'],
        "fixed_code": fixed_code,
        "fixes_applied": results['fixes']
    })
