"""
Module: rag_extractor
Version: 1.1.0
Description: RAG Extractor for AI-PMC Governance — extracts axioms from uploaded PDFs using Gemini API.
             ANOM-016: All error paths return structured dicts (error_code + axioms key).
             ANOM-017: Lazy model init — SOVEREIGN_GEMINI_API_KEY read at call-time, not import-time.
"""

import os
import json
import re
import logging
from typing import List, Dict, Any, Union
from pathlib import Path

import google.generativeai as genai
from PyPDF2 import PdfReader
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ANOM-017 FIX: No module-level side effects. Model is initialised lazily on first call.
_model = None


def _get_model() -> genai.GenerativeModel:
    """
    Lazy initialiser for the Gemini model.
    Reads SOVEREIGN_GEMINI_API_KEY at call-time (not import-time).

    Raises:
        EnvironmentError: If the API key is not set (E001).
    """
    global _model
    if _model is None:
        load_dotenv()
        api_key = os.environ.get("SOVEREIGN_GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "E001: SOVEREIGN_GEMINI_API_KEY not set — set it in .env or environment"
            )
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel("gemini-2.0-flash-exp")
        logger.info("Gemini model initialised (gemini-2.0-flash-exp)")
    return _model


def health_check() -> Dict[str, Any]:
    """
    Return model readiness status for /api/health.

    Returns:
        {"status": "ok", "model": "ready"} or {"status": "error", "error_code": "E001", ...}
    """
    try:
        _get_model()
        return {"status": "ok", "model": "ready"}
    except EnvironmentError as exc:
        return {"status": "error", "error_code": "E001", "message": str(exc)}


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract raw text from a PDF file.

    Args:
        pdf_path: Absolute path to the PDF file.

    Returns:
        Concatenated text from all pages.
    """
    try:
        reader = PdfReader(pdf_path)
        pages = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text)
        return "\n".join(pages)
    except Exception as e:
        logger.error(f"E001: Failed to read PDF '{pdf_path}' — {e}", exc_info=True)
        return ""


def parse_axioms_from_gemini_response(
    response_text: str, engine: str
) -> List[Dict[str, Any]]:
    """
    Parse a Gemini text response into a structured list of axiom objects.

    Args:
        response_text: Raw string returned by the Gemini model.
        engine: One of DEDUCTION | INDUCTION | ABDUCTION.

    Returns:
        List of axiom dicts conforming to the 3-layer schema.
    """
    axioms: List[Dict[str, Any]] = []

    # Attempt JSON block extraction first
    json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and 'axioms' in data:
                return data['axioms']
        except json.JSONDecodeError as exc:
            logger.warning(f"E003: JSON parse failed in Gemini response — {exc}")

    # Fallback: extract LaTeX equations
    latex_pattern = r'\$\$(.*?)\$\$|\$(.*?)\$'
    equations = re.findall(latex_pattern, response_text, re.DOTALL)

    for i, eq in enumerate(equations):
        expr = (eq[0] if eq[0] else eq[1]).strip()
        axioms.append({
            "axiom_id": f"RAG_EXTRACT_{i + 1:03d}",
            "name": f"Extracted Axiom {i + 1}",
            "expression_latex": expr,
            "domain": "unknown",
            "status": "HYPOTHESIZED" if engine == "ABDUCTION" else "CANONICAL",
            "confidence": 0.6,
            "source": "gemini_extraction",
        })

    return axioms


def extract_axioms_from_pdf(
    pdf_path: str, engine: str = "ABDUCTION"
) -> List[Dict[str, Any]]:
    """
    Extract axioms from a PDF file using the Gemini API.

    Args:
        pdf_path: Path to the uploaded PDF file.
        engine: One of DEDUCTION | INDUCTION | ABDUCTION.

    Returns:
        Dict with keys 'axioms' (list) and optionally 'error_code'/'message' on failure.
        ANOM-016 FIX: Never returns a bare list — callers always receive a dict.

    Error codes:
        E001 — File not found / unreadable / model not configured
        E002 — Gemini API timeout
        E003 — Invalid JSON in response / unexpected error
    """
    try:
        model = _get_model()
    except EnvironmentError as exc:
        logger.error(str(exc), exc_info=True)
        return {"error_code": "E001", "message": str(exc), "axioms": []}

    pdf_text = extract_text_from_pdf(pdf_path)
    if not pdf_text.strip():
        logger.warning(f"E001: No text extracted from '{pdf_path}'")
        return {"error_code": "E001", "message": f"No text extracted from '{pdf_path}'", "axioms": []}

    system_prompt = f"""You are an Axiom Extractor for the Sovereign Matrix system.
Extract ALL mathematical formulas, equations, and scientific axioms from the provided document.

Engine Mode: {engine}

Rules:
- For DEDUCTION mode: Extract ONLY deterministic, formulaic, physics-based axioms
- For INDUCTION mode: Extract statistical patterns and empirical relationships
- For ABDUCTION mode: Extract hypotheses and candidate missing axioms

Output format: JSON array with objects containing:
{{
    "axiom_id": "unique_id",
    "name": "Human readable name",
    "expression_latex": "LaTeX formula",
    "domain": "physics/engineering/power/thermodynamics/etc",
    "status": "CANONICAL/INCOMPLETE/ANOMALOUS/HYPOTHESIZED",
    "confidence": 0.0-1.0
}}

Document text follows:
"""

    full_prompt = system_prompt + "\n\n" + pdf_text[:30000]

    try:
        response = model.generate_content(full_prompt)
        axioms = parse_axioms_from_gemini_response(response.text, engine)
        return {"axioms": axioms}  # ANOM-016 FIX: always return dict
    except TimeoutError as exc:
        logger.error(f"E002: Gemini API timeout — {exc}", exc_inc=True)
        return {"error_code": "E002", "message": "Gemini API timeout", "axioms": []}
    except Exception as exc:
        logger.error(f"E003: Gemini extraction error — {exc}", exc_info=True)
        return {"error_code": "E003", "message": str(exc), "axioms": []}


def extract_axioms_from_text(
    text: str, engine: str = "ABDUCTION"
) -> List[Dict[str, Any]]:
    """
    Extract axioms from a raw text string using the Gemini API.

    Args:
        text: Raw document text.
        engine: One of DEDUCTION | INDUCTION | ABDUCTION.

    Returns:
        List of extracted axiom objects in the 3-layer schema.
    """
    try:
        model = _get_model()
    except EnvironmentError as exc:
        logger.error(str(exc), exc_info=True)
        return {"error_code": "E001", "message": str(exc), "axioms": []}

    if not text.strip():
        return {"axioms": []}

    system_prompt = f"""Extract all mathematical formulas and scientific axioms from this text.
Engine Mode: {engine}
Output as JSON array with fields: axiom_id, name, expression_latex, domain, status, confidence.

Text: {text[:30000]}
"""

    try:
        response = model.generate_content(system_prompt)
        axioms = parse_axioms_from_gemini_response(response.text, engine)
        return {"axioms": axioms}
    except TimeoutError as exc:
        logger.error(f"E002: Gemini API timeout — {exc}", exc_info=True)
        return {"error_code": "E002", "message": "Gemini API timeout", "axioms": []}
    except Exception as exc:
        logger.error(f"E003: Gemini extraction error — {exc}", exc_info=True)
        return {"error_code": "E003", "message": str(exc), "axioms": []}
