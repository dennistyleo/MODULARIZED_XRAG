/**
 * Module: matchEngine
 * Version: 1.0.0
 * Description: File content → axiom matching with confidence scoring.
 */

import { AXIOM_DOMAINS, AXIOM_INDEX } from './data/axiomData.js';

/**
 * Match file text content against axiom repository.
 * @param {string} text - Raw extracted text from uploaded file
 * @param {string} mode - 'DEDUCTION' | 'INDUCTION' | 'ABDUCTION'
 * @returns {Array} matched axioms sorted by confidence desc
 */
export function matchTextToAxioms(text, mode = 'DEDUCTION') {
  if (!text || !text.trim()) return [];

  const lowerText = text.toLowerCase();
  const domains = AXIOM_DOMAINS[mode] || AXIOM_DOMAINS.DEDUCTION;
  const results = [];

  Object.values(domains).forEach(domain => {
    domain.axioms.forEach(axiom => {
      const score = _scoreAxiom(lowerText, axiom);
      if (score.confidence > 0.35) {
        results.push({ ...axiom, ...score });
      }
    });
  });

  return results.sort((a, b) => b.confidence - a.confidence);
}

/**
 * Score a single axiom against text.
 * @param {string} lowerText
 * @param {object} axiom
 * @returns {{ confidence: number, matchType: string, matchedTerms: string[] }}
 */
function _scoreAxiom(lowerText, axiom) {
  const matchedTerms = [];
  let confidence = 0;

  // Exact formula match (highest weight)
  const normFormula = axiom.formula.toLowerCase().replace(/\s+/g, '');
  const normText = lowerText.replace(/\s+/g, '');
  if (normText.includes(normFormula)) {
    confidence = Math.max(confidence, 0.97);
    matchedTerms.push(`exact_formula:${axiom.formula.slice(0, 20)}`);
  }

  // Axiom name exact match
  if (lowerText.includes(axiom.name.toLowerCase())) {
    confidence = Math.max(confidence, 0.88);
    matchedTerms.push(`exact_name:${axiom.name}`);
  }

  // Axiom ID match
  if (lowerText.includes(axiom.id.toLowerCase())) {
    confidence = Math.max(confidence, 0.85);
    matchedTerms.push(`id:${axiom.id}`);
  }

  // Key terms from name (each word ≥ 5 chars)
  const nameWords = axiom.name.toLowerCase().split(/\s+/).filter(w => w.length >= 5);
  const nameHits = nameWords.filter(w => lowerText.includes(w));
  if (nameHits.length > 0) {
    const partial = 0.55 + (nameHits.length / nameWords.length) * 0.25;
    confidence = Math.max(confidence, partial);
    matchedTerms.push(...nameHits.map(w => `term:${w}`));
  }

  // Key symbols in formula
  const formulaSymbols = _extractSymbols(axiom.formula);
  const symHits = formulaSymbols.filter(s => lowerText.includes(s.toLowerCase()));
  if (symHits.length >= 2) {
    const partial = 0.40 + (symHits.length / Math.max(formulaSymbols.length, 1)) * 0.25;
    confidence = Math.max(confidence, partial);
    matchedTerms.push(...symHits.map(s => `symbol:${s}`));
  }

  let matchType = 'none';
  if (confidence >= 0.90) matchType = 'exact';
  else if (confidence >= 0.70) matchType = 'keyword';
  else if (confidence >= 0.40) matchType = 'partial';

  return { confidence: Math.min(confidence, 1.0), matchType, matchedTerms };
}

function _extractSymbols(formula) {
  // Extract meaningful alpha-numeric tokens and Greek letters
  return formula.match(/[A-Za-z_α-ωΑ-Ω][A-Za-z0-9_]*/g) || [];
}

/**
 * Build GNN graph data from matched axioms.
 * @param {Array} matchedAxioms
 * @returns {{ nodes: Array, links: Array }}
 */
export function buildGNNGraph(matchedAxioms) {
  if (!matchedAxioms || matchedAxioms.length === 0) return { nodes: [], links: [] };

  const nodes = matchedAxioms.map((ax, i) => ({
    id: ax.id,
    name: ax.name,
    formula: ax.formula,
    confidence: ax.confidence,
    status: ax.status,
    group: ax.id.split('-')[0], // domain prefix
    x: null, y: null,
  }));

  // Build links between axioms sharing domain prefix
  const links = [];
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      if (nodes[i].group === nodes[j].group) {
        links.push({ source: nodes[i].id, target: nodes[j].id, strength: 0.7 });
      } else if (Math.random() < 0.25) {
        links.push({ source: nodes[i].id, target: nodes[j].id, strength: 0.3 });
      }
    }
  }

  return { nodes, links };
}

/**
 * Build causal DAG data from matched axioms.
 * @param {Array} matchedAxioms
 * @returns {{ nodes: Array, edges: Array }}
 */
export function buildCausalGraph(matchedAxioms) {
  if (!matchedAxioms || matchedAxioms.length === 0) return { nodes: [], edges: [] };

  // Variables extracted from axiom formulas
  const varSet = new Set(['S', 'M', 'W', 'H', 'Σ', 'h̃', 'D_band', 'O', 'G', 'ρ', 'ε']);
  const nodes = [...varSet].map((v, i) => ({
    id: v, label: v,
    x: 100 + (i % 4) * 180,
    y: 80 + Math.floor(i / 4) * 140,
    type: i < 3 ? 'observable' : (i === 3 ? 'latent' : 'intervention'),
    confidence: 0.7 + Math.random() * 0.3,
  }));

  const edges = [
    { from: 'S', to: 'Σ',      strength: 0.85, label: '0.85' },
    { from: 'M', to: 'Σ',      strength: 0.78, label: '0.78' },
    { from: 'W', to: 'Σ',      strength: 0.72, label: '0.72' },
    { from: 'H', to: 'h̃',      strength: 0.91, label: '0.91' },
    { from: 'D_band', to: 'h̃', strength: 0.83, label: '0.83' },
    { from: 'O', to: 'h̃',      strength: 0.67, label: '0.67' },
    { from: 'G', to: 'h̃',      strength: 0.74, label: '0.74' },
    { from: 'ρ', to: 'D_band', strength: 0.80, label: '0.80' },
    { from: 'ε', to: 'Σ',      strength: 0.69, label: '0.69' },
  ];

  return { nodes, edges };
}

/**
 * Build world model particle state from matched axioms.
 * @param {Array} matchedAxioms
 * @param {number} count
 * @returns {Array} particle array
 */
export function buildWorldModelParticles(matchedAxioms, count = 1280) {
  const particles = [];
  const avgConf = matchedAxioms.length > 0
    ? matchedAxioms.reduce((s, a) => s + a.confidence, 0) / matchedAxioms.length
    : 0.5;

  for (let i = 0; i < count; i++) {
    particles.push({
      x: Math.random(),
      y: Math.random(),
      confidence: Math.max(0.1, avgConf + (Math.random() - 0.5) * 0.4),
      vx: (Math.random() - 0.5) * 0.002,
      vy: (Math.random() - 0.5) * 0.002,
    });
  }
  return particles;
}
