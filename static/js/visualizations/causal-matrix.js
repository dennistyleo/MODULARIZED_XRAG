/**
 * Module: causal-matrix
 * Version: 1.0.0
 * Description: Causal Matrix Visualization — Canvas 2D animated edge-trace graph
 */

class CausalMatrixVisualization {
    constructor(containerId, width, height) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.warn(`CausalMatrixVisualization: container '${containerId}' not found`);
        }
        this.width       = width  || this.container?.clientWidth  || 800;
        this.height      = height || this.container?.clientHeight || 600;
        this.canvas      = null;
        this.ctx         = null;
        this.animationId = null;
        this.nodes       = [];
        this.edges       = [];
        this.colors = {
            DEDUCTION: '#39FF14',
            INDUCTION: '#00D4FF',
            ABDUCTION: '#FF6B1A',
        };
    }

    // ── Public API ─────────────────────────────────────────────────────────

    /**
     * Initialise / re-render the causal matrix.
     * @param {Array}  axioms    List of axiom objects.
     * @param {Array}  anomalies List of anomaly objects.
     * @param {string} engine    DEDUCTION | INDUCTION | ABDUCTION
     */
    init(axioms, anomalies, engine = 'ABDUCTION') {
        if (!this.container) return;

        this.destroy();

        this.canvas = document.createElement('canvas');
        this.canvas.width  = this.width;
        this.canvas.height = this.height;
        Object.assign(this.canvas.style, {
            width: '100%', height: '100%',
            backgroundColor: '#FFFFFF', borderRadius: '12px',
        });
        this.container.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');

        this._buildGraph(axioms, anomalies);
        this._startAnimation();
        this._setupClickHandler();

        this._resizeHandler = () => this.resize();
        window.addEventListener('resize', this._resizeHandler);
    }

    updateData(axioms, anomalies, engine) {
        this._buildGraph(axioms, anomalies);
    }

    resize() {
        if (!this.container || !this.canvas) return;
        this.width  = this.container.clientWidth;
        this.height = this.container.clientHeight;
        this.canvas.width  = this.width;
        this.canvas.height = this.height;

        // Re-layout nodes
        const anomalyNodes = this.nodes.filter(n => n.type === 'anomaly');
        const axiomNodes   = this.nodes.filter(n => n.type === 'axiom');
        anomalyNodes.forEach((n, i) => { n.x = 100;                n.y = 100 + i * 80; });
        axiomNodes.forEach((n, i)   => { n.x = this.width - 150;   n.y = 100 + i * 60; });
    }

    destroy() {
        if (this.animationId) cancelAnimationFrame(this.animationId);
        if (this._resizeHandler) window.removeEventListener('resize', this._resizeHandler);
        this.canvas?.remove();
        this.canvas = this.ctx = null;
        this.animationId = null;
        this.nodes = [];
        this.edges = [];
    }

    // ── Private helpers ────────────────────────────────────────────────────

    _buildGraph(axioms, anomalies) {
        this.nodes = [];
        this.edges = [];

        (anomalies ?? []).forEach((anomaly, idx) => {
            this.nodes.push({
                id: anomaly.id ?? `anomaly_${idx}`,
                name: anomaly.name ?? `Anomaly ${idx + 1}`,
                type: 'anomaly',
                x: 100,
                y: 100 + idx * 80,
                confidence: 1.0,
            });
        });

        (axioms ?? []).forEach((axiom, idx) => {
            this.nodes.push({
                id:         axiom.axiom_id ?? `axiom_${idx}`,
                name:       axiom.name     ?? axiom.axiom_id ?? `Axiom ${idx + 1}`,
                type:       'axiom',
                status:     axiom.status,
                x:          this.width - 150,
                y:          100 + idx * 60,
                confidence: axiom.confidence ?? 0.7,
            });
        });

        const anomalyNodes = this.nodes.filter(n => n.type === 'anomaly');
        const axiomNodes   = this.nodes.filter(n => n.type === 'axiom');

        anomalyNodes.forEach(source => {
            axiomNodes
                .filter(a => a.status === 'HYPOTHESIZED')
                .forEach(target => {
                    this.edges.push({ source, target, strength: target.confidence, is_causal: true });
                });
        });

        // Soft links between related axioms
        for (let i = 0; i < axiomNodes.length; i++) {
            for (let j = i + 1; j < axiomNodes.length; j++) {
                if (Math.random() > 0.8) {
                    this.edges.push({
                        source:    axiomNodes[i],
                        target:    axiomNodes[j],
                        strength:  0.3,
                        is_causal: false,
                    });
                }
            }
        }
    }

    _startAnimation() {
        let pulse = 0;
        const animate = () => {
            if (!this.ctx) return;
            this.ctx.clearRect(0, 0, this.width, this.height);
            this._drawGrid();
            this.edges.forEach(e => this._drawEdge(e, pulse));
            this.nodes.forEach(n => this._drawNode(n, pulse));
            pulse = (pulse + 0.02) % 1;
            this.animationId = requestAnimationFrame(animate);
        };
        this.animationId = requestAnimationFrame(animate);
    }

    _drawGrid() {
        const step = 40;
        this.ctx.beginPath();
        this.ctx.strokeStyle = '#E9ECEF';
        this.ctx.lineWidth   = 0.5;
        for (let x = 0; x < this.width; x += step) {
            this.ctx.moveTo(x, 0); this.ctx.lineTo(x, this.height);
        }
        for (let y = 0; y < this.height; y += step) {
            this.ctx.moveTo(0, y); this.ctx.lineTo(this.width, y);
        }
        this.ctx.stroke();
    }

    _drawEdge(edge, pulse) {
        if (!edge.source || !edge.target) return;

        const { x: sx, y: sy } = edge.source;
        const { x: ex, y: ey } = edge.target;
        const mx = (sx + ex) / 2;
        const my = (sy + ey) / 2 - 30;

        // Base curve
        let color = edge.is_causal ? '#FF6B1A' : '#D4AF37';
        if (edge.strength > 0.7) color = '#39FF14';

        this.ctx.beginPath();
        this.ctx.moveTo(sx, sy);
        this.ctx.quadraticCurveTo(mx, my, ex, ey);
        this.ctx.strokeStyle   = color;
        this.ctx.lineWidth     = edge.is_causal ? 2 : 1;
        this.ctx.setLineDash(edge.is_causal ? [8, 6] : []);
        this.ctx.stroke();

        // Animated pulse for causal edges
        if (edge.is_causal) {
            this.ctx.beginPath();
            this.ctx.moveTo(sx, sy);
            this.ctx.quadraticCurveTo(mx, my, ex, ey);
            this.ctx.strokeStyle    = '#FFD700';
            this.ctx.lineWidth      = 2;
            this.ctx.setLineDash([10, 20]);
            this.ctx.lineDashOffset = -pulse * 30;
            this.ctx.stroke();
        }

        this.ctx.setLineDash([]);

        // Arrowhead
        const angle = Math.atan2(ey - my, ex - mx);
        const ax    = ex - 12 * Math.cos(angle);
        const ay    = ey - 12 * Math.sin(angle);
        this.ctx.fillStyle = color;
        this.ctx.beginPath();
        this.ctx.moveTo(ax, ay);
        this.ctx.lineTo(ax - 6, ay - 4);
        this.ctx.lineTo(ax - 6, ay + 4);
        this.ctx.fill();
    }

    _drawNode(node, pulse) {
        // Pulsing glow for anomaly sources
        if (node.type === 'anomaly') {
            this.ctx.beginPath();
            this.ctx.arc(node.x, node.y, 20 + Math.sin(pulse * Math.PI * 2) * 3, 0, Math.PI * 2);
            this.ctx.fillStyle = 'rgba(255,77,77,0.2)';
            this.ctx.fill();
        }

        // Fill color
        let fill = '#6C757D';
        if (node.type === 'anomaly')         fill = '#FF4D4D';
        else if (node.status === 'CANONICAL')    fill = '#D4AF37';
        else if (node.status === 'HYPOTHESIZED') fill = '#00D4FF';
        else if (node.status === 'ANOMALOUS')    fill = '#FF6B1A';

        this.ctx.beginPath();
        this.ctx.arc(node.x, node.y, 14, 0, Math.PI * 2);
        this.ctx.fillStyle   = fill;
        this.ctx.fill();
        this.ctx.strokeStyle = '#FFFFFF';
        this.ctx.lineWidth   = 2;
        this.ctx.stroke();

        // Confidence arc
        if (node.confidence) {
            this.ctx.beginPath();
            this.ctx.arc(node.x, node.y, 17, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * node.confidence);
            this.ctx.strokeStyle = '#39FF14';
            this.ctx.lineWidth   = 2;
            this.ctx.stroke();
        }

        // Label
        this.ctx.font      = 'bold 11px Monaco, monospace';
        this.ctx.fillStyle = '#1A1A1A';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(node.name.substring(0, 18), node.x, node.y - 22);

        if (node.type === 'axiom' && node.status) {
            this.ctx.font      = '8px monospace';
            this.ctx.fillStyle = fill;
            this.ctx.fillText(node.status, node.x, node.y + 26);
        }
    }

    _setupClickHandler() {
        if (!this.canvas) return;
        this.canvas.addEventListener('click', (event) => {
            const rect   = this.canvas.getBoundingClientRect();
            const scaleX = this.canvas.width  / rect.width;
            const scaleY = this.canvas.height / rect.height;
            const mx     = (event.clientX - rect.left) * scaleX;
            const my     = (event.clientY - rect.top)  * scaleY;

            for (const node of this.nodes) {
                const dx = mx - node.x;
                const dy = my - node.y;
                if (Math.sqrt(dx * dx + dy * dy) < 20) {
                    if (node.type === 'axiom' && typeof window.onAxiomSelected === 'function') {
                        window.onAxiomSelected(node.id);
                    }
                    break;
                }
            }
        });
    }
}

export default CausalMatrixVisualization;
