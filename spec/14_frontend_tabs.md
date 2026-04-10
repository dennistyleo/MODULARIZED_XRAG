# Frontend Tabs Specification

Version: 1.0.0

## Architecture
All tab components self-register via ComponentRegistry.
No hardcoded IDs in parent shell code.

## ComponentRegistry Interface (JavaScript)
class ComponentRegistry:
  registerTab({id, label, order, component})
  getTab(id)       → component or null
  listTabs()       → array sorted by order
  on(event, cb)    → subscribe to data events
  emit(event, data) → publish data event

## Self-Registration Pattern
// In each tab module:
export function register(registry) {
    const component = new MyTab();
    registry.registerTab({
        id:        'my_tab',
        label:     'My Tab',
        order:     3,
        component: component
    });
    return component;
}

## Tab Lifecycle Hooks
bind(containerElement) → called when DOM container is created
onActivate()           → called when tab becomes visible
onDeactivate()         → called when tab is hidden
onData(eventName, data) → called when subscribed event fires

## Required Tabs
| ID          | Label        | Order | Subscribes to           |
|-------------|--------------|-------|-------------------------|
| upload      | Upload       | 1     | —                        |
| gnn         | GNN          | 2     | data:gnn:updated        |
| world_model | World Model  | 3     | data:worldmodel:updated |
| causal      | Causal       | 4     | data:causal:updated     |
| report      | Report       | 5     | data:report:ready       |
| hitl        | HITL Review  | 6     | HITL_REQUEST            |

## Data Events (SocketIO → frontend)
- data:extracted        → triggers upload tab update
- data:gnn:updated      → triggers GNN tab update
- data:worldmodel:updated → triggers World Model tab update
- data:causal:updated   → triggers Causal tab update
- data:report:ready     → triggers Report tab update
- hitl:request          → triggers HITL modal open

## Graceful Degradation Rule
Each onData() implementation must guard for null/empty data:
  if (!data || !data.nodes) {
      console.warn('No data for tab:', this.id);
      return;
  }

## Error Codes
- E009: ComponentRegistry not initialized before tab mount

## Test Points
- TAB_001: All 6 tabs auto-register after main.js loads
- TAB_002: listTabs() returns tabs in ascending order
- TAB_003: Unknown tab ID returns null from getTab()
- TAB_004: onData() with null input does not throw
- TAB_005: hitl:request event opens HITL modal without page reload

## Upload Tab Details

The Upload tab is the entry point for all audit sessions.

| Element | Behavior |
|---------|----------|
| Drop zone | Accepts PDF, CSV, JSON via drag-and-drop or click |
| Progress bar | Shows upload + extraction progress (0–100%) |
| Extraction summary | Displayed after DATA_EXTRACTED event received |
| Confidence gauge | Visual indicator (0–100%), color-coded by threshold |
| HITL trigger | If overall confidence < 85%, HITL modal opens automatically |

```javascript
// Upload tab auto-triggers HITL on low confidence
this.registry.on('data:rag:extracted', (data) => {
    this._showExtractionSummary(data);
    if (data.confidence < 0.85) {
        this.registry.emit('hitl:open', { reason: 'LOW_CONFIDENCE', data });
    }
});
```

## Report Tab Details

The Report tab displays the final L5 AUDIT_SYNTHESIS output.

| Element | Behavior |
|---------|----------|
| HTML report body | Rendered directly from L5 output (sanitized HTML) |
| Metadata bar | Displays trace_id, session_id, report_type, timestamp |
| Download buttons | JSON / PDF / CSV — each triggers a separate export endpoint |
| Print button | Invokes browser print dialog; report is pre-styled for A4 |
| Report ID | Displayed in header, copied to clipboard on click |

Export endpoint mapping:
- JSON  → `GET /api/report/{report_id}?format=json`
- PDF   → `GET /api/report/{report_id}?format=pdf`
- CSV   → `GET /api/report/{report_id}?format=csv`

## HITL Review Tab Details

The HITL Review tab provides an inline alternative to the modal for reviewing and correcting extracted data.

| Element | Behavior |
|---------|----------|
| Activation | Tab becomes active when HITL_REQUEST event is received |
| Content | Same data table and edit panel as the HITL modal |
| Correction history | Lists all corrections made in the current session |
| Relationship to modal | Modal and tab share the same HITL state; closing modal does not clear tab |
| Post-confirm | Tab remains visible with read-only correction history after HITL_RESPONSE sent |

```javascript
this.registry.on('hitl:request', (payload) => {
    this._activate();           // switch to this tab
    this._renderReviewPanel(payload);
});
```

## Default Active Tab

| State | Active Tab | Reason |
|-------|-----------|--------|
| Page load (engine not initialized) | Upload | Only enabled tab |
| After DATA_EXTRACTED | GNN | Auto-switch to visualize extraction (configurable) |
| After HITL_REQUEST | HITL Review | Auto-switch to review panel |
| After REPORT_READY | Report | Auto-switch to show final output |

Auto-switch behavior is controlled by `SOVEREIGN_AUTO_TAB_SWITCH` (default: `true`).
When `false`, tab switching requires explicit user click.

## Tab Switching Animation

```css
.tab-panel {
    opacity: 0;
    transition: opacity 0.2s ease;
    pointer-events: none;
}

.tab-panel.active {
    opacity: 1;
    pointer-events: auto;
}
```

Rules:
- No layout shift during switch (all panels occupy the same grid area)
- Outgoing panel fades to opacity 0 before incoming panel fades in
- Animation is skipped if `prefers-reduced-motion: reduce` is set

## Uninitialized State (Pre-Engine)

Before the user clicks "INITIALIZE ENGINE", the following rules apply:

| Tab | State | Visual Indicator |
|-----|-------|-----------------|
| Upload | ENABLED | Normal appearance |
| GNN | DISABLED | Lock icon + tooltip: "Initialize engine first" |
| World Model | DISABLED | Lock icon + tooltip: "Initialize engine first" |
| Causal Matrix | DISABLED | Lock icon + tooltip: "Initialize engine first" |
| Report | DISABLED | Lock icon + tooltip: "Initialize engine first" |
| HITL Review | DISABLED | Hidden (not shown in tab bar) |

```javascript
_setUninitializedState() {
    const lockedTabs = ['gnn', 'world_model', 'causal', 'report'];
    lockedTabs.forEach(id => {
        const tab = this.registry.getTab(id);
        if (!tab) return;
        tab.setDisabled(true, 'Initialize engine first');
    });
}
```

Graceful degradation: clicking a disabled tab shows the tooltip but does NOT throw an error.
