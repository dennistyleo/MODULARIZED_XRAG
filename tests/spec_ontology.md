# SOVEREIGN MATRIX — UI Spec Ontology
# Version: 1.0.0
# This is the authoritative source of truth for all QA tests.

## Spec Hierarchy (Priority Order)

| Priority | Source | What It Defines |
|---|---|---|
| L1 | Canva JSON DAHGkUzWygw | Exact px positions, hex colors, fonts, border-radius, border-width, gradient stops |
| L2 | OP-01.png / Op-02.png / Op-03.png | Pixel-level visual reference, layout composition |
| L3 | Verbal requirements | Continuous scroll, responsive, video swappability, no tab routing |
| L4 | FROZEN landing page | Landing page HTML must NOT be modified |

---

## HARD CONSTRAINTS

- SPEC_FREEZE_001: Landing page HTML/CSS is APPROVED. Zero modifications permitted.
- SPEC_LAYOUT_001: Continuous scroll only. No JS tab routing. All sections always visible.
- SPEC_RESP_001:   Layout must adapt to 1366x768, 1920x1080, 1090x1920 and all viewports.


## COLORS (from L1 — Canva JSON)

TOKEN                 HEX       ELEMENT
gold-primary          #c9a349   Dividers, AXIOM REPO bar, card border (solid)
gold-dark-shadow      #734f22   Secondary/inner divider
sidebar-border-start  #ff3131   Sidebar container border gradient top
gradient-end          #ff914d   Sidebar + card border gradient bottom
card-border-start     #ffde59   Card container border gradient top
op03-green-flank      #00bf63   OP-03 header flanks + nav bar (NOT used on OP-01/02)
button-dark-green     #224d2b   MANUAL AXIOM SELECTION button (OP-02 only)
button-bright-green   #00bf63   GENERATE AUDIT REPORT (OP-02 only)
button-lime           #9eff1f   All 3 action buttons (OP-03 only)
banner-teal           #0a714e   DEDUCTION SPECIFIED EVALUATION bar (OP-03 only)
logic-text-green      #89ef65   TRACE ENGINE LOGIC / DEDUCTIVE TIMESTAMP text (OP-03)
flank-fill-op01-02    #000000   OP-01 and OP-02 header octagon flanks


## FONTS (from L1 — Canva JSON)

ID             Name         Usage
YAFdtQi73Xs   Montserrat   All general text, buttons, headers
YACgEZ1cb1Q   Arimo        Supporting text
YADrvjt3J6s   Horizon      AXIOM REPO label only


## BORDERS

Element               Border-color            Width   Radius
Sidebar container     #ff3131 -> #ff914d      15px    15px
Card container        #ffde59 -> #ff914d      13px    13px
AXIOM REPO bar        #c9a349 (solid, fill)   8px     8px
Card header label     #c9a349 (solid stroke)  8px     0
Gold vertical divider #c9a349 (solid fill)    ~14px   0
Dark gold shadow      #734f22 (solid fill)    ~5px    0
TRACE ENGINE LOGIC    #c9a349 (solid stroke)  8px     8px
DEDUCTIVE TIMESTAMP   #c9a349 (solid stroke)  8px     8px
DEDUCTION banner      #c9a349 (solid stroke)  83px (border-radius)


## PLACEHOLDER CONTRACT (auto-matching feature)

Every video/image placeholder MUST satisfy ALL of the following:

1. FIXED SHAPE:
   - overflow: hidden on container
   - aspect-ratio CSS OR padding-top (56.2225% for 16:9) on container
   - border-radius applied to container per spec column above

2. INNER MEDIA AUTO-FILL:
   - position: absolute; top: 0; left: 0; width: 100%; height: 100%
   - object-fit: cover (fills container, crops excess)
   - Works for: <video>, <iframe>, <img>, .mp4, .webm, .png, .jpg

3. SWAPPABLE SOURCE:
   - Each placeholder has a `src` or `data-src` attribute
   - Changing the attribute replaces media without layout shift
   - No JS framework dependency required for swap

4. RESPONSIVE:
   - Container width is % or flex-based, never fixed px
   - Media scales with container at all viewport sizes

VIOLATIONS:
   - overflow: visible on placeholder container
   - fixed px width/height on media element inside placeholder
   - missing object-fit
   - missing position: absolute on inner media


## OP-PAGE STRUCTURE

### OP-01 (ABDUCTION MODE — Black Flanks)
- Flank color: #000000
- Sidebar: red-orange gradient border
- Cards: AXIOM APPLIED + GNN MODEL (2 cards)
- Videos: 3 sidebar slots + GNN card video
- Buttons: none (upload is via separate zone)

### OP-02 (ABDUCTION MODE — Black Flanks)
- Flank color: #000000
- Sidebar: red-orange gradient border
- Cards: 2x AXIOM APPLIED + WORLD MODEL + CAUSAL MODEL
- Buttons: MANUAL AXIOM SELECTION (#224d2b) + GENERATE AUDIT REPORT (#00bf63)

### OP-03 (DEDUCTION MODE — GREEN Flanks)
- Flank color: #00bf63 (KEY DISTINCTION from OP-01/02)
- DEDUCTION SPECIFIED EVALUATION banner: #0a714e fill + #c9a349 border
- 3-column grid: each column has DEDUCTION AXIOM APPLIED header + GNN MODEL header
- Buttons: lime (#9eff1f) for all 3 actions
- TRACE ENGINE LOGIC + DEDUCTIVE TIMESTAMP boxes: #000000 fill, #89ef65 text


## QA TEST MATRIX

ID                Description                                    Tool
SPEC_FREEZE_001   Landing page DOM unchanged from approved state  Playwright
SPEC_VISUAL_001   OP-01 screenshot matches OP-01.png ±2%         Playwright+Pillow
SPEC_VISUAL_002   OP-02 screenshot matches Op-02.png ±2%         Playwright+Pillow
SPEC_VISUAL_003   OP-03 screenshot matches Op-03.png ±2%         Playwright+Pillow
SPEC_COLOR_*      All colors present on correct elements          Playwright getComputedStyle
SPEC_BORDER_*     border-color, border-width, border-radius       Playwright getComputedStyle
SPEC_FONT_*       font-family, font-size, font-weight             Playwright getComputedStyle
SPEC_DIM_*        Element W/H within ±2px at 1366px viewport      Playwright getBoundingClientRect
SPEC_PH_*         Placeholder auto-matching contract              Playwright getComputedStyle
SPEC_RESP_*       Layout valid at 320/768/1366/1920px             Playwright viewport resize
SPEC_STRUCT_*     All labels, sections, IDs present              Playwright querySelector
SPEC_OP03_*       OP-03 specific: green flanks, 3-col, lime btns  Playwright
