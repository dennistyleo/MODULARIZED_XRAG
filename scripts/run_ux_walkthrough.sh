#!/usr/bin/env bash
# =============================================================================
# run_ux_walkthrough.sh  |  Sovereign Matrix UX Walkthrough  |  SaaS Grade
# =============================================================================
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "═══════════════════════════════════════════════════════════════"
echo "  Sovereign Matrix — UX Walkthrough Test (SaaS Production)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ── Pre-flight: server up? ───────────────────────────────────────────────────
echo "→ Checking server status..."
if ! curl -sf "${SOVEREIGN_BASE_URL:-http://localhost:8080}/api/health" >/dev/null; then
    echo "❌  Server not running. Start with: python app.py"
    exit 1
fi
echo "  ✓ Server is up"

# ── Install test dependencies ────────────────────────────────────────────────
echo ""
echo "→ Installing test dependencies..."
pip install --quiet \
    pytest pytest-rerunfailures pytest-html \
    "pytest-playwright>=0.4" \
    pillow numpy
playwright install chromium --with-deps --quiet 2>/dev/null || true
echo "  ✓ Dependencies ready"

# ── Directories ──────────────────────────────────────────────────────────────
mkdir -p test_videos reports tests/snapshots

# ── Run tests ────────────────────────────────────────────────────────────────
echo ""
echo "→ Running UX walkthrough (retries=3, html-report)..."
echo ""

UPDATE_FLAG=""
if [ "${UPDATE_SNAPSHOTS:-false}" = "true" ]; then
    echo "  📸 UPDATE_SNAPSHOTS=true — refreshing visual baselines"
    UPDATE_FLAG="--update-snapshots"
fi

python -m pytest tests/e2e/test_ux_walkthrough.py \
    -v \
    --tb=short \
    --maxfail=5 \
    --reruns=3 \
    --reruns-delay=1 \
    --durations=15 \
    --html=reports/ux_walkthrough_report.html \
    --self-contained-html \
    --video=on-first-retry \
    --screenshot=only-on-failure \
    ${UPDATE_FLAG} \
    "$@"

EXIT_CODE=$?

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Results"
echo "═══════════════════════════════════════════════════════════════"
[ -f reports/ux_walkthrough_report.html ] && echo "  📊 Report : reports/ux_walkthrough_report.html"
VIDEO_COUNT=$(find test_videos -name "*.webm" 2>/dev/null | wc -l | tr -d ' ')
SNAP_COUNT=$(find tests/snapshots -name "*.png" 2>/dev/null | wc -l | tr -d ' ')
echo "  🎥 Videos    : $VIDEO_COUNT"
echo "  📸 Snapshots : $SNAP_COUNT"
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "  ✅ WALKTHROUGH PASSED"
else
    echo "  ❌ WALKTHROUGH FAILED (exit $EXIT_CODE)"
    echo "     Check test_videos/ for failure recordings"
fi
echo "═══════════════════════════════════════════════════════════════"
exit $EXIT_CODE
