/**
 * Module: ComponentRegistry
 * Version: 1.0.0
 * Description: Self-registration system for all frontend tab components.
 *              No hardcoded IDs — components register themselves.
 */

export class ComponentRegistry {
    constructor() {
        /** @type {Map<string, object>} */
        this._tabs = new Map();
        /** @type {Map<string, Function[]>} */
        this._listeners = new Map();
    }

    /**
     * Register a tab component.
     * @param {{ id: string, label: string, order: number, component: object|null }} config
     * @returns {ComponentRegistry}
     */
    registerTab(config) {
        if (!config.id || !config.label) {
            console.error('[Registry] E009: registerTab requires id and label', config);
            return this;
        }
        this._tabs.set(config.id, config);
        console.log(`[Registry] Tab registered: ${config.id}`);
        return this;
    }

    /**
     * Retrieve a registered tab by ID.
     * @param {string} id
     * @returns {object|undefined}
     */
    getTab(id) {
        return this._tabs.get(id);
    }

    /**
     * List all registered tabs, sorted by order.
     * @returns {object[]}
     */
    listTabs() {
        return Array.from(this._tabs.values()).sort((a, b) => (a.order ?? 99) - (b.order ?? 99));
    }

    /**
     * Set disabled state on a tab button.
     * @param {string} id
     * @param {boolean} disabled
     * @param {string} [tooltip]
     */
    setTabDisabled(id, disabled, tooltip = '') {
        const btn = document.getElementById(`tab-btn-${id}`);
        if (!btn) return;
        btn.setAttribute('data-disabled', disabled ? 'true' : 'false');
        btn.setAttribute('aria-disabled', disabled ? 'true' : 'false');
        if (tooltip) btn.setAttribute('title', tooltip);
        if (disabled) btn.style.pointerEvents = 'none';
        else btn.style.pointerEvents = '';
    }

    /**
     * Switch to a tab by ID. Calls onActivate() on the component if defined.
     * @param {string} tabId
     */
    switchTab(tabId) {
        const tab = this._tabs.get(tabId);
        if (!tab) {
            console.warn(`[Registry] Tab not found: ${tabId}`);
            return;
        }
        if (tab.disabled) {
            console.warn(`[Registry] Tab ${tabId} is disabled`);
            return;
        }

        // Update button states
        document.querySelectorAll('.tab-btn').forEach(btn => {
            const isActive = btn.dataset.tab === tabId;
            btn.classList.toggle('active', isActive);
            btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
        });

        // Update panel visibility
        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.toggle('active', pane.id === `tab-${tabId}`);
            pane.classList.toggle('hidden', pane.id !== `tab-${tabId}`);
        });

        // Lifecycle hook
        if (tab.component?.onActivate) {
            try { tab.component.onActivate(); }
            catch (e) { console.error(`[Registry] onActivate error for ${tabId}:`, e); }
        }

        this.emit('tab:switched', { tabId });
    }

    /**
     * Subscribe to a registry event.
     * @param {string} event
     * @param {Function} callback
     */
    on(event, callback) {
        if (!this._listeners.has(event)) this._listeners.set(event, []);
        this._listeners.get(event).push(callback);
    }

    /**
     * Emit a registry event to all subscribers.
     * @param {string} event
     * @param {*} data
     */
    emit(event, data) {
        const cbs = this._listeners.get(event) ?? [];
        cbs.forEach(cb => {
            try { cb(data); }
            catch (e) { console.error(`[Registry] Listener error on "${event}":`, e); }
        });
    }
}
