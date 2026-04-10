# HTML UI Specification

Version: 1.0.0

## Technology Stack
- Markup:       HTML5 (semantic elements)
- Styles:       Vanilla CSS (no frameworks)
- JavaScript:   ES6 modules (type="module")
- Visualization: D3.js v7 for causal tree and GNN graph
- Realtime:     Socket.IO v4 client

## Layout (100vh Viewport-Locked)
+--------------------------------------------------+
|  Header (56px)  – logo, title, status badge      |
+--------------------------------------------------+
|  Tab Bar (48px) – Upload | GNN | World | Causal  |
|                           | Report | HITL         |
+--------------------------------------------------+
|  Tab Content (calc(100vh - 104px), overflow:auto) |
|                                                  |
|  [Active tab panel rendered here]                |
+--------------------------------------------------+

## Unique Element IDs (required for browser testing)
- sovereign-header
- tab-bar
- tab-upload, tab-gnn, tab-world-model, tab-causal, tab-report, tab-hitl
- panel-upload, panel-gnn, panel-world-model, panel-causal, panel-report
- upload-input (file input)
- upload-btn
- run-audit-btn
- hitl-modal (dialog element)
- hitl-confirm-btn
- hitl-cancel-btn
- status-badge
- landing-overlay

## Color Palette (CSS Custom Properties)
--color-bg:         #0a0d14
--color-surface:    #131722
--color-border:     #1e2535
--color-accent:     #4f8ef7
--color-success:    #22c55e
--color-warning:    #f59e0b
--color-danger:     #ef4444
--color-text:       #e2e8f0
--color-text-muted: #94a3b8

## Typography
Font: Inter (Google Fonts)
Weights: 400, 500, 600, 700
Base size: 14px

## Responsive Breakpoints
- >= 1280px: full multi-column layout
- 768–1279px: single-column, tabs scroll horizontally
- < 768px: warning banner "Use desktop for best experience"

## Print / PDF Export
- @media print: hide tab bar, header buttons; show all panels stacked
- Multi-page support: page-break-before: always between sections

## Accessibility
- All inputs: aria-label
- Tab role="tab", tabpanel role="tabpanel", tablist role="tablist"
- Modal: role="dialog", aria-modal="true"
- Status badge: aria-live="polite"

## Performance
- CSS and JS bundled < 200 KB total (gzip)
- First paint < 1 second on localhost
- D3 canvas redraws throttled to 60 fps

## Test Points
- HTML_001: All unique IDs exist in DOM after page load
- HTML_002: Tab click switches active panel without full reload
- HTML_003: File upload via drag-drop populates upload-input value
- HTML_004: @media print hides tab-bar and header buttons
- HTML_005: Landing overlay dismisses on upload completion
