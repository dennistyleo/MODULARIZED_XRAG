#!/usr/bin/env bash
# =============================================================================
# pre_commit_elab.sh  |  Sovereign Matrix RTL Pre-Commit Gate  |  v1.1.0
# Runs: (1) lint_rtl.py, (2) Vivado elaboration (if available)
# Exit 0 = allow commit  |  Exit 1 = block commit
# =============================================================================
set -euo pipefail
cd "$(git rev-parse --show-toplevel)/fpga"

echo "═══════════════════════════════════════════"
echo "  Sovereign RTL Pre-Commit Gate"
echo "═══════════════════════════════════════════"
ERRORS=0

# ── Step 1: Python lint ──────────────────────────────────────────────────────
echo ""
echo "→ [1/2] Running lint_rtl.py..."
if python3 scripts/lint_rtl.py; then
    echo "  ✓ lint PASS"
else
    echo "  ✗ lint FAIL — fix errors above before committing"
    ERRORS=$((ERRORS + 1))
fi

# ── Step 2: Vivado elaboration (skip if Vivado not on PATH) ─────────────────
echo ""
echo "→ [2/2] Vivado elaboration check..."
VIVADO_BIN=$(which vivado 2>/dev/null || true)

if [ -z "$VIVADO_BIN" ]; then
    echo "  ⚠  Vivado not on PATH — skipping elaboration (run in Vivado terminal)"
    echo "     To enable: source /tools/Xilinx/Vivado/2022.2/settings64.sh"
else
    ELAB_TCL=$(mktemp /tmp/elab_XXXX.tcl)
    cat > "$ELAB_TCL" <<'EOF'
set rtl_files [glob -directory rtl *.v]
set tb_files  [glob -directory sim *.v]
create_project -in_memory -part xczu7ev-ffvc1156-2-e
read_verilog $rtl_files
synth_design -rtl -name rtl_1
EOF
    if vivado -mode batch -source "$ELAB_TCL" -log /tmp/elab_vivado.log -nojournal 2>&1 \
       | grep -qE "ERROR:|CRITICAL"; then
        echo "  ✗ Vivado elaboration FAIL — see /tmp/elab_vivado.log"
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✓ Vivado elaboration PASS"
    fi
    rm -f "$ELAB_TCL"
fi

# ── Result ───────────────────────────────────────────────────────────────────
echo ""
if [ "$ERRORS" -eq 0 ]; then
    echo "  ✅ Pre-commit gate PASSED"
    exit 0
else
    echo "  ❌ Pre-commit gate FAILED ($ERRORS step(s) failed)"
    echo "     Commit blocked. Fix all errors and re-stage."
    exit 1
fi
