# Axiom Generator Schema & Pipeline Specification

Version: 1.0.0

## Overview
This spec defines the canonical data structure, generation pipeline, prompt templates, search index, and validation rules for the Axiom Repository.

---

## Part 1: Axiom Schema (JSON-LD Format)

Each axiom in the repository is a JSON object with three progressive-disclosure layers.

```json
{
  "$schema": "https://axiom-repo.ai/schema/v1",
  "axiom_id": "NEWTON_GRAV_01",
  "version": "2.3.1",
  "last_modified": "2026-04-11T10:30:00Z",

  "layer_1_audit_header": {
    "name": "Universal Gravitation",
    "expression_latex": "F = G \\frac{m_1 m_2}{r^2}",
    "expression_pddl": "(= (gravitational-force ?b1 ?b2) (* G (* (mass ?b1) (mass ?b2)) (/ 1 (* (distance ?b1 ?b2) (distance ?b1 ?b2)))))",
    "domain": "Celestial Mechanics",
    "status": "ANOMALOUS",
    "health": {
      "phenomena_explained_count": 12,
      "phenomena_total_count": 15,
      "explanation_ratio": 0.8
    },
    "badge_color": "red"
  },

  "layer_2_summary": {
    "derivation_path": {
      "type": "primitive",
      "parent_axioms": []
    },
    "explains": [
      { "phenomenon_id": "KEPLER_LAWS", "confidence": 0.98 },
      { "phenomenon_id": "TIDAL_FORCES", "confidence": 0.85 },
      { "phenomenon_id": "PLANETARY_ORBITS_LOW_V", "confidence": 0.95 }
    ],
    "fails_to_explain": [
      {
        "phenomenon_id": "MERCURY_PERIHELION",
        "gap_description": "43 arcseconds per century",
        "gap_quantitative": 43.0,
        "gap_units": "arcsec/century"
      },
      {
        "phenomenon_id": "GRAVITATIONAL_LENSING",
        "gap_description": "No prediction of light bending",
        "gap_quantitative": null
      }
    ],
    "abductive_gap": {
      "semantic_distance": 0.72,
      "spectrum_position": "right_of_center",
      "closest_canonical_axiom": "EINSTEIN_FIELD_EQ_04",
      "candidate_missing_axiom": {
        "axiom_id": "EINSTEIN_FIELD_EQ_04",
        "expression_latex": "R_{\\mu\\nu} - \\frac{1}{2}g_{\\mu\\nu}R + \\Lambda g_{\\mu\\nu} = \\frac{8\\pi G}{c^4} T_{\\mu\\nu}",
        "semantic_distance_from_current": 0.72
      }
    }
  },

  "layer_3_full_detail": {
    "algebraic": {
      "primary_decomposition": {
        "input_ideal": "I = ⟨A2, A3, A4, A5, Q⟩",
        "associated_primes": [
          "⟨d₂, m₁, F_g, F_c, wp-1⟩",
          "⟨m₂, d₁, F_g, F_c, wp-1⟩",
          "⟨m₂, m₁, F_g, F_c, wp-1⟩",
          "⟨F_c - F_g, m₁d₁ - m₂d₂, wp-1, F_g(d₁+d₂)² - m₁m₂G, ...⟩"
        ],
        "generators_tested": [
          { "generator": "F_g(d₁+d₂)² - m₁m₂G = 0", "derives_q": true,  "rejection_reason": null },
          { "generator": "d₂ = 0",                   "derives_q": false, "rejection_reason": "projection_does_not_match_Q" },
          { "generator": "m₂ = 0",                   "derives_q": false, "rejection_reason": "projection_does_not_match_Q" }
        ]
      }
    },
    "symbolic_transformation": {
      "source_axiom_id": "NEWTON_GRAV_01",
      "target_axiom_id": "EINSTEIN_FIELD_EQ_04",
      "rewrite_steps": [
        "S₀ = {A₁, A₂, A₅}",
        "→ {A₁', A₂, A₅}",
        "→ {A₁'', A₂, A₅}",
        "→ {W₂, A₅}",
        "→ {W₂, A₅'}",
        "→ {W₄'}",
        "→ {W₄}"
      ],
      "semantic_distance": 0.72,
      "llm_justification": "Moderate change: preserves conservation principles while generalizing metric to curved spacetime."
    },
    "pddl_representation": {
      "domain_name": "celestial-mechanics",
      "action": {
        "name": "gravitational-acceleration",
        "parameters": ["?body1 - celestial-body", "?body2 - celestial-body"],
        "preconditions": [
          "(mass ?body1 ?m1)",
          "(mass ?body2 ?m2)",
          "(distance ?body1 ?body2 ?r)"
        ],
        "effects": [
          "(increase (velocity ?body1) (* G ?m2 (/ 1 (* ?r ?r))))",
          "(increase (velocity ?body2) (* G ?m1 (/ 1 (* ?r ?r))))"
        ]
      }
    }
  }
}
```

---

## Part 2: Generation Pipeline (4 Stages)

### Stage 1: Ingestion
**Inputs:** Canonical axioms, phenomenon descriptions, prior work outputs.

**AG Actions:**
- Parse LaTeX expressions into symbolic form
- Extract or assign unique `axiom_id` (format: `{DOMAIN_ABBREV}_{NAME}_{##}`)
- Classify domain
- Set initial status: `CANONICAL` if no known anomalies, else `INCOMPLETE`

### Stage 2: Anomaly Detection
**Inputs:** Phenomena each axiom explains; contradictory observations.

**AG Actions:**
- For each axiom: compare `explains` set against `fails_to_explain` set
- If `fails_to_explain` is non-empty → update status to `ANOMALOUS`
- Compute: `health.explanation_ratio = explained_count / total_count`
- Attach gap descriptions (qualitative and quantitative)

### Stage 3: Abductive Inference (AI Noether Integration)
**Inputs:** Anomalous axiom set `{A1...Ak}`, target phenomenon `Q`.

**AG Actions:**
- Call AI Noether's `reason()` function (Algorithm 1 in paper)
- For each generator `g` that successfully derives `Q`:
  - Create a new `HYPOTHESIZED` axiom object
  - Store derivation proof (`derives_q: true`)
  - Link back via `candidate_missing_axiom`

### Stage 4: Semantic Distance & Transformation Trail
**Inputs:** Source axiom (anomalous), target axiom (canonical or hypothesized).

**AG Actions:**
- Compute semantic distance via LLM pairwise comparison + merge sort
- Generate atomic rewrite steps:
  - Change variable: `t → τ`
  - Change operator: `d/dt → ∇_τ`
  - Add term: `+ Λg_μν`
- Store in `layer_3_full_detail.symbolic_transformation`

---

## Part 3: AG Prompt Template

```
You are the Axiom Generator (AG) for the AI Noether-Newton repository.

Generate a complete axiom object in JSON following the schema below.

INPUT:
- Axiom name: {name}
- Domain: {domain}
- Canonical expression (LaTeX): {latex}
- Phenomena it explains: {list}
- Known anomalies (if any): {list}

OUTPUT REQUIREMENTS:
1. Generate a unique axiom_id (format: DOMAIN_ABBREV_NAME_##)
2. Set status to CANONICAL if no anomalies, else ANOMALOUS
3. Compute health.explanation_ratio
4. If anomalous, provide abductive_gap with semantic_distance estimate
5. Include PDDL translation of the expression
6. Keep all fields, use null for unknown

Return ONLY valid JSON, no explanatory text.
```

---

## Part 4: Repository Search Index

```json
{
  "index_version": "1.0",
  "last_built": "2026-04-11T10:30:00Z",
  "axioms_by_status": {
    "CANONICAL":    ["EULER_BERNOULLI_01", "FOURIER_HEAT_02"],
    "INCOMPLETE":   ["MAXWELL_EM_03"],
    "ANOMALOUS":    ["NEWTON_GRAV_01"],
    "HYPOTHESIZED": ["EINSTEIN_FIELD_EQ_04"]
  },
  "axioms_by_domain": {
    "Celestial Mechanics": ["NEWTON_GRAV_01", "KEPLER_LAW_01", "EINSTEIN_FIELD_EQ_04"],
    "Electromagnetism":    ["MAXWELL_EM_01", "MAXWELL_EM_02", "MAXWELL_EM_03"],
    "Thermodynamics":      ["CLAUSIUS_2ND_01", "BOLTZMANN_ENTROPY_01"]
  },
  "anomaly_groups": [
    {
      "anomalous_axiom": "NEWTON_GRAV_01",
      "failing_phenomena": ["MERCURY_PERIHELION", "GRAVITATIONAL_LENSING"],
      "candidate_fix": "EINSTEIN_FIELD_EQ_04",
      "semantic_distance": 0.72
    }
  ]
}
```

---

## Part 5: Validation Rules

| Rule | Check | Action if Violated |
|------|-------|-------------------|
| Uniqueness | `axiom_id` not already in index | Generate new ID with incremented number |
| Expression well-formedness | LaTeX compiles; PDDL parses | Reject; request human correction |
| Status consistency | `ANOMALOUS` requires non-empty `fails_to_explain` | Reject; add at least one anomaly |
| Candidate fix consistency | If `candidate_missing_axiom` present, `semantic_distance` must be 0–1 | Reject; compute distance first |
| Derivation closure | If `derivation_path.type == derived`, all parent_axioms must exist | Reject; ingest parents first |
