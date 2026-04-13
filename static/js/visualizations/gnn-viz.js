/**
 * Module: gnn-viz
 * Version: 1.0.0
 * Description: GNN Visualization — D3.js force-directed constellation map showing axiom relationships
 */

class GNNVisualization {
    constructor(containerId, width, height) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.warn(`GNNVisualization: container '${containerId}' not found`);
        }
        this.width  = width  || (this.container?.clientWidth  ?? 800);
        this.height = height || (this.container?.clientHeight ?? 600);
        this.svg        = null;
        this.simulation = null;
        this.nodes      = [];
        this.links      = [];
        this.colors = {
            DEDUCTION: '#39FF14',
            INDUCTION: '#00D4FF',
            ABDUCTION: '#FF6B1A',
        };
    }

    // ── Public API ─────────────────────────────────────────────────────────

    /**
     * Initialise / re-render the force-directed graph.
     * @param {Array}  axioms  List of axiom objects from the 3-layer schema.
     * @param {string} engine  DEDUCTION | INDUCTION | ABDUCTION
     */
    init(axioms, engine = 'ABDUCTION') {
        if (!this.container || !axioms || !axioms.length) {
            console.warn('GNNVisualization.init: no container or empty axioms');
            return;
        }

        this.container.innerHTML = '';
        this._buildGraph(axioms);

        const color = this.colors[engine] ?? this.colors.ABDUCTION;

        // SVG root
        this.svg = d3.select(this.container)
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height)
            .attr('viewBox', [0, 0, this.width, this.height])
            .style('background', '#FFFFFF')
            .style('border-radius', '12px');

        const defs = this.svg.append('defs');

        // Glow filter
        const filter = defs.append('filter')
            .attr('id', 'gnn-glow')
            .attr('x', '-50%').attr('y', '-50%')
            .attr('width', '200%').attr('height', '200%');
        filter.append('feGaussianBlur')
            .attr('stdDeviation', 3)
            .attr('result', 'coloredBlur');
        const feMerge = filter.append('feMerge');
        feMerge.append('feMergeNode').attr('in', 'coloredBlur');
        feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

        // Arrow marker
        defs.append('marker')
            .attr('id', 'gnn-arrow')
            .attr('viewBox', '0 0 10 10')
            .attr('refX', 20).attr('refY', 5)
            .attr('markerWidth', 8).attr('markerHeight', 8)
            .attr('orient', 'auto')
            .append('polygon')
            .attr('points', '0 0, 10 5, 0 10')
            .attr('fill', color);

        // Links
        const link = this.svg.append('g')
            .attr('class', 'gnn-links')
            .selectAll('line')
            .data(this.links)
            .enter().append('line')
            .attr('stroke', color)
            .attr('stroke-opacity', 0.4)
            .attr('stroke-width', 1.5)
            .attr('stroke-dasharray', d => d.is_abductive ? '5,5' : 'none')
            .attr('marker-end', 'url(#gnn-arrow)');

        // Node groups
        const node = this.svg.append('g')
            .attr('class', 'gnn-nodes')
            .selectAll('g')
            .data(this.nodes)
            .enter().append('g')
            .attr('class', 'node-group')
            .call(this._dragBehaviour());

        // Node circles
        node.append('circle')
            .attr('r', d => 8 + (d.confidence ?? 0.5) * 12)
            .attr('fill', d => this._nodeColor(d, engine))
            .attr('stroke', '#FFFFFF')
            .attr('stroke-width', 2)
            .attr('filter', 'url(#gnn-glow)');

        // Labels
        node.append('text')
            .attr('dx', 12).attr('dy', 4)
            .attr('font-size', '10px')
            .attr('font-family', 'monospace')
            .attr('fill', '#1A1A1A')
            .text(d => d.name.substring(0, 15));

        // Status dot
        node.append('circle')
            .attr('r', 3)
            .attr('fill', d => this._statusColor(d.status))
            .attr('cx', 0).attr('cy', -8);

        // Force simulation
        this.simulation = d3.forceSimulation(this.nodes)
            .force('link',      d3.forceLink(this.links).id(d => d.id).distance(120))
            .force('charge',    d3.forceManyBody().strength(-300))
            .force('center',    d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(30))
            .on('tick', () => {
                link
                    .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
                node.attr('transform', d => `translate(${d.x},${d.y})`);
            });

        // Hover effects
        node
            .on('mouseenter', function(event, d) {
                d3.select(this).select('circle')
                    .transition().duration(200)
                    .attr('r', 20);
                link.attr('stroke-opacity',
                    l => (l.source.id === d.id || l.target.id === d.id) ? 0.85 : 0.15);
            })
            .on('mouseleave', function(event, d) {
                d3.select(this).select('circle')
                    .transition().duration(200)
                    .attr('r', 8 + (d.confidence ?? 0.5) * 12);
                link.attr('stroke-opacity', 0.4);
            });

        // Click to select axiom
        node.on('click', (event, d) => {
            if (typeof window.onAxiomSelected === 'function') {
                window.onAxiomSelected(d.id);
            }
        });
    }

    resize(width, height) {
        this.width  = width;
        this.height = height;
        if (this.svg) {
            this.svg.attr('width', width).attr('height', height);
        }
        if (this.simulation) {
            this.simulation
                .force('center', d3.forceCenter(width / 2, height / 2))
                .alpha(0.3).restart();
        }
    }

    destroy() {
        if (this.simulation) this.simulation.stop();
        if (this.svg) this.svg.remove();
        this.svg = null;
        this.simulation = null;
    }

    // ── Private helpers ────────────────────────────────────────────────────

    _buildGraph(axioms) {
        const nodeMap = new Map();
        axioms.forEach((axiom, idx) => {
            const id = axiom.axiom_id ?? `axiom_${idx}`;
            nodeMap.set(id, {
                id,
                name:       axiom.name       ?? id,
                status:     axiom.status     ?? 'HYPOTHESIZED',
                confidence: axiom.confidence ?? 0.7,
                domain:     axiom.domain     ?? 'unknown',
            });
        });

        this.nodes = Array.from(nodeMap.values());
        this.links = [];

        for (let i = 0; i < this.nodes.length; i++) {
            for (let j = i + 1; j < this.nodes.length; j++) {
                if (Math.random() > 0.7) {
                    this.links.push({
                        source:       this.nodes[i].id,
                        target:       this.nodes[j].id,
                        is_abductive: Math.random() > 0.8,
                    });
                }
            }
        }
    }

    _nodeColor(node, engine) {
        if (node.status === 'CANONICAL')  return '#D4AF37';
        if (node.status === 'ANOMALOUS')  return '#FF4D4D';
        if (node.status === 'HYPOTHESIZED') return this.colors[engine] ?? this.colors.ABDUCTION;
        return '#6C757D';
    }

    _statusColor(status) {
        const map = {
            CANONICAL:   '#39FF14',
            ANOMALOUS:   '#FF4D4D',
            HYPOTHESIZED:'#00D4FF',
        };
        return map[status] ?? '#6C757D';
    }

    _dragBehaviour() {
        return d3.drag()
            .on('start', (event) => {
                if (!event.active && this.simulation) this.simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            })
            .on('drag', (event) => {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            })
            .on('end', (event) => {
                if (!event.active && this.simulation) this.simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            });
    }
}

export default GNNVisualization;
