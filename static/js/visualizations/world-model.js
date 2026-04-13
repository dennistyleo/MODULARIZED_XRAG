/**
 * Module: world-model
 * Version: 1.0.0
 * Description: World Model Visualization — Three.js 3D projection lattice of candidate axioms
 */

class WorldModelVisualization {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.warn(`WorldModelVisualization: container '${containerId}' not found`);
        }
        this.scene       = null;
        this.camera      = null;
        this.renderer    = null;
        this.cubes       = [];
        this.animationId = null;
        this.colors = {
            DEDUCTION: 0x39FF14,
            INDUCTION: 0x00D4FF,
            ABDUCTION: 0xFF6B1A,
        };
    }

    // ── Public API ─────────────────────────────────────────────────────────

    /**
     * Initialise / re-render the 3-D projection lattice.
     * @param {Array}  axioms  List of axiom objects from the 3-layer schema.
     * @param {string} engine  DEDUCTION | INDUCTION | ABDUCTION
     */
    init(axioms, engine = 'ABDUCTION') {
        if (!this.container || !axioms) {
            console.warn('WorldModelVisualization.init: no container or axioms');
            return;
        }

        this.destroy();

        const engineColor = this.colors[engine] ?? this.colors.ABDUCTION;

        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xFFFFFF);
        this.scene.fog = new THREE.FogExp2(0xFFFFFF, 0.008);

        // Camera
        this.camera = new THREE.PerspectiveCamera(
            45,
            this.container.clientWidth / this.container.clientHeight,
            0.1,
            1000
        );
        this.camera.position.set(8, 6, 12);
        this.camera.lookAt(0, 0, 0);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.container.appendChild(this.renderer.domElement);

        // Lighting
        this.scene.add(new THREE.AmbientLight(0x404060));

        const dirLight = new THREE.DirectionalLight(0xFFFFFF, 1);
        dirLight.position.set(1, 2, 1);
        this.scene.add(dirLight);

        const backLight = new THREE.DirectionalLight(0x88AACC, 0.5);
        backLight.position.set(-1, 1, -1);
        this.scene.add(backLight);

        const fillLight = new THREE.PointLight(0xCCAA88, 0.3);
        fillLight.position.set(0, 2, 0);
        this.scene.add(fillLight);

        // Grid
        const grid = new THREE.GridHelper(20, 20, 0xCCCCCC, 0xEEEEEE);
        grid.position.y = -1.5;
        this.scene.add(grid);

        // Axiom cubes
        const gridSize = Math.min(5, Math.ceil(Math.sqrt(axioms.length)));
        const spacing  = 1.8;
        const offset   = (gridSize - 1) * spacing / 2;
        this.cubes = [];

        axioms.forEach((axiom, idx) => {
            const row = Math.floor(idx / gridSize);
            const col = idx % gridSize;
            const x   = col * spacing - offset;
            const z   = row * spacing - offset;
            const y   = Math.sin(row * 0.8 + col * 0.8) * 0.5;

            let color = engineColor;
            if (axiom.status === 'CANONICAL') color = 0xD4AF37;
            if (axiom.status === 'ANOMALOUS') color = 0xFF4D4D;

            const geometry = new THREE.BoxGeometry(0.8, 0.8, 0.8);
            const material = new THREE.MeshStandardMaterial({
                color,
                metalness: 0.6,
                roughness: 0.3,
                emissive:          axiom.status === 'HYPOTHESIZED' ? color : 0x000000,
                emissiveIntensity: 0.2,
            });

            const cube = new THREE.Mesh(geometry, material);
            cube.position.set(x, y, z);
            cube.userData = { axiom, originalY: y };

            // Wireframe edges
            cube.add(new THREE.LineSegments(
                new THREE.EdgesGeometry(geometry),
                new THREE.LineBasicMaterial({ color: 0xFFFFFF })
            ));

            this.scene.add(cube);
            this.cubes.push(cube);

            this._addLabel(axiom.name ?? `Axiom ${idx + 1}`, x, y + 0.7, z);
        });

        // Particle system
        const pCount = 800;
        const pPositions = new Float32Array(pCount * 3);
        for (let i = 0; i < pCount; i++) {
            pPositions[i * 3]     = (Math.random() - 0.5) * 15;
            pPositions[i * 3 + 1] = (Math.random() - 0.5) * 8;
            pPositions[i * 3 + 2] = (Math.random() - 0.5) * 12 - 4;
        }
        const pGeo = new THREE.BufferGeometry();
        pGeo.setAttribute('position', new THREE.BufferAttribute(pPositions, 3));
        const particles = new THREE.Points(pGeo, new THREE.PointsMaterial({
            color: engineColor, size: 0.05, transparent: true, opacity: 0.5,
        }));
        this.scene.add(particles);

        // Raycaster for click
        this._setupRaycaster();

        // Animation loop
        let time = 0;
        const animate = () => {
            this.animationId = requestAnimationFrame(animate);
            time += 0.01;

            particles.rotation.y = time * 0.1;
            particles.rotation.x = Math.sin(time * 0.2) * 0.1;

            this.cubes.forEach((cube, i) => {
                cube.position.y = cube.userData.originalY + Math.sin(time * 1.5 + i) * 0.05;
            });

            this.camera.position.x = 8 + Math.sin(time * 0.1) * 0.5;
            this.camera.lookAt(0, 0, 0);

            this.renderer.render(this.scene, this.camera);
        };
        animate();

        this._resizeHandler = () => this.resize();
        window.addEventListener('resize', this._resizeHandler);
    }

    resize() {
        if (!this.container || !this.renderer) return;
        const w = this.container.clientWidth;
        const h = this.container.clientHeight;
        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(w, h);
    }

    destroy() {
        if (this.animationId) cancelAnimationFrame(this.animationId);
        if (this.renderer) this.renderer.dispose();
        if (this._resizeHandler) window.removeEventListener('resize', this._resizeHandler);
        while (this.container?.firstChild) {
            this.container.removeChild(this.container.firstChild);
        }
        this.scene = this.camera = this.renderer = null;
        this.cubes = [];
        this.animationId = null;
    }

    // ── Private helpers ────────────────────────────────────────────────────

    _addLabel(text, x, y, z) {
        const canvas = document.createElement('canvas');
        canvas.width  = 256;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#1A1A1A';
        ctx.fillRect(0, 0, 256, 64);
        ctx.font      = 'Bold 14px Monaco, monospace';
        ctx.fillStyle = '#D4AF37';
        ctx.textAlign = 'center';
        ctx.fillText(text.substring(0, 20), 128, 37);

        const sprite = new THREE.Sprite(
            new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), depthTest: false })
        );
        sprite.scale.set(1.5, 0.4, 1);
        sprite.position.set(x, y, z);
        this.scene.add(sprite);
    }

    _setupRaycaster() {
        this.raycaster = new THREE.Raycaster();
        this._mouse    = new THREE.Vector2();

        this.renderer.domElement.addEventListener('click', (event) => {
            const rect = this.renderer.domElement.getBoundingClientRect();
            this._mouse.x =  ((event.clientX - rect.left) / rect.width)  * 2 - 1;
            this._mouse.y = -((event.clientY - rect.top)  / rect.height) * 2 + 1;

            this.raycaster.setFromCamera(this._mouse, this.camera);
            const intersects = this.raycaster.intersectObjects(this.cubes);

            if (intersects.length > 0) {
                const cube  = intersects[0].object;
                const axiom = cube.userData.axiom;

                this.cubes.forEach(c => { c.material.emissiveIntensity = 0; });
                cube.material.emissiveIntensity = 0.4;

                if (typeof window.onAxiomSelected === 'function') {
                    window.onAxiomSelected(axiom.axiom_id);
                }
            }
        });
    }
}

export default WorldModelVisualization;
