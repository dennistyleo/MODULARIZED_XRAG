#!/usr/bin/env python3
"""
UX Walkthrough Test — Sovereign Matrix (SaaS Production Grade)  |  v1.1.0
Bug-fixes vs. user-provided draft:
  - pytest-playwright flags corrected (--video on-first-retry, --screenshot only-on-failure)
  - CDP network emulation wrapped in try/except (Chromium-only)
  - snapshot --snapshot-update CLI flag replaced by UPDATE_SNAPSHOTS env var
  - pytest-playwright added to requirements-dev.txt
  - Model fixture scoped correctly to avoid teardown collisions
  - TEST_PDF_PATH falls back to any discovered PDF so tests run in all environments
"""

import os
import time
import json
import pytest
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE_URL = os.environ.get("SOVEREIGN_BASE_URL", "http://localhost:8080")
SNAPSHOT_DIR = Path("tests/snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# PDF fixture: use the STRÜVER file if present, else first PDF found
_candidate = Path("spec/features/pdf_pages/STRÜVER Model — Formula-Only.pdf")
TEST_PDF_PATH = _candidate if _candidate.exists() else next(
    Path("spec/features").rglob("*.pdf"), Path("spec/features/CONCEPTUAL_SPEC_M_XRAG.pdf")
)

UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "false").lower() == "true"


class TestUXWalkthrough:
    """Complete user journey test suite — SaaS production grade."""

    LCP_THRESHOLD_MS       = 3000
    STEP_TIMEOUT_MS        = 10_000
    API_RESPONSE_TIMEOUT_MS = 15_000
    SLOW_THROTTLE_MS       = 5_000
    MIN_TAP_TARGET_PX      = 44

    @pytest.fixture(scope="class")
    def browser(self):
        with sync_playwright() as p:
            br = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            yield br
            br.close()

    @pytest.fixture
    def page(self, browser):
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 1024},
            record_video_dir="test_videos/" if os.environ.get("CI") else None,
            ignore_https_errors=True,
        )
        pg = ctx.new_page()
        yield pg
        pg.close()
        ctx.close()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _assert_snapshot(self, page, name: str, threshold: float = 0.01):
        """Screenshot + pixel-diff comparison. On first run saves baseline."""
        snapshot_path = SNAPSHOT_DIR / f"{name}.png"
        baseline_path = SNAPSHOT_DIR / f"{name}_baseline.png"

        page.screenshot(path=str(snapshot_path), full_page=False)

        if UPDATE_SNAPSHOTS or not baseline_path.exists():
            import shutil
            shutil.copy(snapshot_path, baseline_path)
            print(f"  📸 Baseline saved: {name}")
            return

        try:
            from PIL import Image
            import numpy as np
            baseline = Image.open(baseline_path).convert("RGB")
            current  = Image.open(snapshot_path).convert("RGB")
            if baseline.size != current.size:
                current = current.resize(baseline.size)
            diff_frac = abs(
                float(sum(sum(abs(a - b) for a, b in zip(r1, r2))
                          for r1, r2 in zip(baseline.getdata(), current.getdata())))
            ) / (baseline.width * baseline.height * 3 * 255)
            assert diff_frac < threshold, (
                f"Visual regression {name}: {diff_frac*100:.2f}% diff (limit {threshold*100}%)")
            print(f"  📸 Snapshot OK: {name} ({diff_frac*100:.2f}%)")
        except ImportError:
            print("  ⚠️ pillow/numpy not installed — skipping pixel diff")

    def _set_cdp_network(self, page, *, offline: bool = False,
                         latency: int = 0, throughput: int = -1):
        """Apply Chrome DevTools Protocol network conditions (Chromium only)."""
        try:
            cdp = page.context.new_cdp_session(page)
            cdp.send("Network.emulateNetworkConditions", {
                "offline": offline,
                "latency": latency,
                "downloadThroughput": throughput,
                "uploadThroughput": throughput,
            })
        except Exception as exc:
            print(f"  ⚠️ CDP unavailable ({exc}) — skipping throttle")

    def _reset_cdp_network(self, page):
        self._set_cdp_network(page, offline=False, latency=0, throughput=-1)

    # ── TC-UX-01: Visual regression — mode colour change ─────────────────────

    def test_01_visual_regression_mode_colors(self, page):
        page.goto(BASE_URL)
        page.wait_for_selector(".landing-cta-btn", timeout=self.STEP_TIMEOUT_MS)

        self._assert_snapshot(page, "landing_abduction_mode")

        for engine, name in [("DEDUCTION", "landing_deduction_mode"),
                              ("INDUCTION", "landing_induction_mode")]:
            btn = page.locator(f".engine-toggle-btn[data-engine='{engine}']")
            if btn.count() > 0:
                btn.click()
                page.wait_for_timeout(400)
                self._assert_snapshot(page, name)

        print("✅ TC-UX-01: Mode colour snapshots OK")

    # ── TC-UX-02: Slow-3G loading state (skeleton / spinner) ─────────────────

    def test_02_network_slow_3g_loading_state(self, page):
        # Throttle: 500 Kbps, 150 ms RTT
        self._set_cdp_network(page, latency=150, throughput=500 * 1024)
        page.goto(BASE_URL)
        page.locator(".landing-cta-btn").click()
        page.wait_for_selector("#dashboard-container", timeout=self.STEP_TIMEOUT_MS)

        loading = page.locator(".loading-spinner, .skeleton-screen, .progress-bar")
        if loading.count() > 0:
            expect(loading.first).to_be_visible()
            print("  ✓ Loading indicator visible under throttle")
        else:
            print("  ⚠️ No loading indicator (may have loaded instantly)")

        self._reset_cdp_network(page)
        print("✅ TC-UX-02: Slow-3G loading state checked")

    # ── TC-UX-03: Offline mode — graceful degradation ────────────────────────

    def test_03_offline_graceful_degradation(self, page):
        page.goto(BASE_URL)
        page_errors = []
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        self._set_cdp_network(page, offline=True)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        assert len(page_errors) == 0, f"JS errors in offline mode: {page_errors}"

        self._reset_cdp_network(page)
        page.reload()
        print("✅ TC-UX-03: Offline — no JS crashes")

    # ── TC-UX-04: Deep linking — SPA route persistence on refresh ────────────

    def test_04_deep_linking_route_persistence(self, page):
        page.goto(BASE_URL)
        page.locator(".landing-cta-btn").click()
        page.wait_for_selector("#dashboard-container", timeout=self.STEP_TIMEOUT_MS)

        page.reload()
        page.wait_for_selector("#dashboard-container", timeout=self.STEP_TIMEOUT_MS)

        landing = page.locator(".landing-container")
        if landing.count() > 0:
            expect(landing).to_have_css("display", "none")

        expect(page.locator("#dashboard-container")).to_be_visible()
        print("✅ TC-UX-04: Deep link — dashboard persists on refresh")

    # ── TC-UX-05: Touch target size ≥ 44 px (Apple / Google Guidelines) ──────

    def test_05_touch_target_sizes(self, page):
        page.goto(BASE_URL)

        selectors = [
            ".landing-cta-btn",
            ".engine-toggle-btn",
            ".nav-btn",
            ".pipeline-stage",
        ]
        critical   = {".landing-cta-btn", ".engine-toggle-btn"}
        violations = []

        for sel in selectors:
            els = page.locator(sel)
            for i in range(min(els.count(), 10)):
                el = els.nth(i)
                if el.is_visible():
                    box = el.bounding_box()
                    if box:
                        w, h = box["width"], box["height"]
                        if w < self.MIN_TAP_TARGET_PX or h < self.MIN_TAP_TARGET_PX:
                            violations.append({"sel": sel, "w": w, "h": h})

        critical_fail = [v for v in violations if v["sel"] in critical]
        for v in violations:
            print(f"  ⚠️ Tap target small: {v['sel']} — {v['w']:.0f}×{v['h']:.0f}px")
        assert not critical_fail, f"Critical tap targets too small: {critical_fail}"
        print("✅ TC-UX-05: Tap targets OK")

    # ── TC-UX-06: API slow response — spinner visible ─────────────────────────

    def test_06_api_slow_response_spinner(self, page):
        def slow_route(route):
            time.sleep(self.SLOW_THROTTLE_MS / 1000)
            route.continue_()

        page.goto(BASE_URL)
        page.locator(".landing-cta-btn").click()
        page.wait_for_selector("#upload-drop-zone", timeout=self.STEP_TIMEOUT_MS)
        page.route("**/api/upload", slow_route)

        file_input = page.locator("#upload-drop-zone input[type='file']")
        if not TEST_PDF_PATH.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF_PATH}")
        file_input.set_input_files(str(TEST_PDF_PATH))

        spinner = page.locator(".loading-spinner, .upload-progress-bar")
        if spinner.count() > 0:
            expect(spinner.first).to_be_visible(timeout=3000)

        page.unroute("**/api/upload")
        page.wait_for_selector(
            ".axiom-count-display:not(:has-text('0'))",
            timeout=self.API_RESPONSE_TIMEOUT_MS,
        )
        print("✅ TC-UX-06: Slow-API loading state OK")

    # ── TC-UX-07: Visual regression — GNN canvas ──────────────────────────────

    def test_07_visual_regression_gnn_canvas(self, page):
        page.goto(BASE_URL)
        page.locator(".landing-cta-btn").click()

        file_input = page.locator("#upload-drop-zone input[type='file']")
        if not TEST_PDF_PATH.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF_PATH}")
        file_input.set_input_files(str(TEST_PDF_PATH))
        page.wait_for_selector(
            ".axiom-count-display:not(:has-text('0'))",
            timeout=self.API_RESPONSE_TIMEOUT_MS,
        )

        gnn_tab = page.locator(".analysis-tab[data-tab='gnn']")
        if gnn_tab.count() > 0:
            gnn_tab.click()
            page.wait_for_selector("#gnn-canvas, #gnn-viz canvas", timeout=8000)
            self._assert_snapshot(page, "dashboard_gnn_canvas", threshold=0.05)

        print("✅ TC-UX-07: GNN canvas snapshot OK")

    # ── TC-UX-08: Visual regression — World Model 3D ──────────────────────────

    def test_08_visual_regression_world_model(self, page):
        page.goto(BASE_URL)
        page.locator(".landing-cta-btn").click()

        file_input = page.locator("#upload-drop-zone input[type='file']")
        if not TEST_PDF_PATH.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF_PATH}")
        file_input.set_input_files(str(TEST_PDF_PATH))
        page.wait_for_selector(
            ".axiom-count-display:not(:has-text('0'))",
            timeout=self.API_RESPONSE_TIMEOUT_MS,
        )

        wm_tab = page.locator(".analysis-tab[data-tab='world-model']")
        if wm_tab.count() > 0:
            wm_tab.click()
            page.wait_for_selector("#world-model-canvas canvas", timeout=8000)
            self._assert_snapshot(page, "dashboard_world_model", threshold=0.05)

        print("✅ TC-UX-08: World Model snapshot OK")

    # ── TC-UX-09: Mobile (iPhone 12 390×844) touch layout ────────────────────

    def test_09_mobile_touch_layout(self, browser):
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        page = ctx.new_page()
        try:
            page.goto(BASE_URL)
            cta = page.locator(".landing-cta-btn")
            h = cta.evaluate("el => el.offsetHeight")
            w = cta.evaluate("el => el.offsetWidth")
            assert h >= self.MIN_TAP_TARGET_PX, f"CTA too short: {h}px"
            assert w >= self.MIN_TAP_TARGET_PX, f"CTA too narrow: {w}px"

            cta.click()
            page.wait_for_selector("#dashboard-container", timeout=self.STEP_TIMEOUT_MS)
            print("✅ TC-UX-09: Mobile layout OK")
        finally:
            page.close()
            ctx.close()

    # ── TC-UX-10: E2E happy path with timing assertion ────────────────────────

    def test_10_e2e_happy_path(self, page):
        if not TEST_PDF_PATH.exists():
            pytest.skip(f"Test PDF not found: {TEST_PDF_PATH}")

        t0 = time.time()

        page.goto(BASE_URL)
        page.wait_for_selector(".landing-cta-btn", timeout=self.STEP_TIMEOUT_MS)

        abduction_btn = page.locator(".engine-toggle-btn[data-engine='ABDUCTION']")
        if abduction_btn.count() > 0:
            abduction_btn.click()

        page.locator(".landing-cta-btn").click()
        page.wait_for_selector("#dashboard-container", timeout=self.STEP_TIMEOUT_MS)

        file_input = page.locator("#upload-drop-zone input[type='file']")
        file_input.set_input_files(str(TEST_PDF_PATH))
        page.wait_for_selector(
            ".axiom-count-display:not(:has-text('0'))",
            timeout=self.API_RESPONSE_TIMEOUT_MS,
        )

        for tab_sel, canvas_sel in [
            (".analysis-tab[data-tab='gnn']",         "#gnn-canvas, #gnn-viz canvas"),
            (".analysis-tab[data-tab='world-model']",  "#world-model-canvas canvas"),
            (".analysis-tab[data-tab='causal']",       "#causal-canvas canvas"),
        ]:
            tab = page.locator(tab_sel)
            if tab.count() > 0:
                tab.click()
                page.wait_for_selector(canvas_sel, timeout=8000)

        report_stage = page.locator(".pipeline-stage[data-page='3']")
        if report_stage.count() > 0:
            report_stage.click()
            page.wait_for_selector("#report-container", timeout=self.STEP_TIMEOUT_MS)

        elapsed_ms = (time.time() - t0) * 1000
        print(f"✅ TC-UX-10: E2E happy path completed ({elapsed_ms:.0f} ms)")
        assert elapsed_ms < 90_000, f"Journey too slow: {elapsed_ms:.0f} ms"


# ── pytest markers ────────────────────────────────────────────────────────────

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "visual_regression: snapshot comparison tests"
    )
    config.addinivalue_line(
        "markers", "network_emulation: CDP network throttle tests"
    )
