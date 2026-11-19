"""Opt-in Linux/Chromium smoke for an already-running PUBLIC stateless preview.

Requires an approved Playwright 1.56.0 + Chromium installation. No install,
server start, host setting, pairing, production login or privileged write is done.
Output must be a NEW directory; screenshots contain only synthetic local data.
"""

import argparse
import hashlib
import json
import re
import traceback
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--base-url",
    default="http://127.0.0.1:4183",
    help="Owner-approved public planner URL, no credentials/path/query",
)
parser.add_argument(
    "--output-dir",
    required=True,
    type=Path,
    help="NEW private evidence directory, never overwritten",
)
args = parser.parse_args()
BASE = args.base_url.rstrip("/")
url = urlsplit(BASE)
if (
    url.scheme not in {"http", "https"}
    or not url.hostname
    or url.path
    or url.query
    or url.fragment
    or url.username
    or url.password
):
    parser.error("base URL must be an HTTP(S) origin without credentials/path/query")
DEST = args.output_dir
DEST.mkdir(parents=True, mode=0o700, exist_ok=False)
checks = []
errors = []
requests = []
console = []


def check(name, passed, details=None):
    checks.append({"name": name, "passed": bool(passed), "details": details})
    assert passed, name


result = {
    "schema": "openbot.browser-smoke/1",
    "scope": "Chromium headless in disposable Linux browser contexts against the public stateless planner. No paired gateway, native WebView, live chat, provider/PC/IDE/social account, full accessibility audit or release acceptance.",
    "checks": checks,
    "page_errors": errors,
    "console_errors": console,
    "requests": requests,
    "upstream_app_executed": False,
    "screenshots": [],
    "base_url": BASE,
    "shared_html_sha256": hashlib.sha256(
        (ROOT / "studio/web/index.html").read_bytes()
    ).hexdigest(),
}
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        result["browser_version"] = browser.version
        context = browser.new_context(
            viewport={"width": 1440, "height": 960},
            device_scale_factor=1,
            color_scheme="light",
        )
        page = context.new_page()
        page.set_default_timeout(5000)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on(
            "console", lambda m: console.append(m.text) if m.type == "error" else None
        )
        page.on(
            "request", lambda r: requests.append({"method": r.method, "url": r.url})
        )
        response = page.goto(BASE, wait_until="networkidle")
        check(
            "served_html_matches_current_source",
            hashlib.sha256(response.body()).digest()
            == hashlib.sha256((ROOT / "studio/web/index.html").read_bytes()).digest(),
        )
        check(
            "desktop_openbot_os_title", page.title() == "OpenBot OS · Your companions"
        )
        check(
            "desktop_visible_light_three_column_layout",
            page.locator(".contact-panel").is_visible()
            and page.locator(".conversation-panel").is_visible()
            and page.locator(".details-panel").is_visible(),
            page.locator(".workspace").evaluate(
                "(el)=>getComputedStyle(el).gridTemplateColumns"
            ),
        )
        check(
            "default_is_unpaired_local_not_live",
            page.locator("#gateway-badge").inner_text() == "Local workspace"
            and "No computer connected" in page.locator("#details-panel").inner_text(),
        )
        check(
            "blueprints_not_fabricated_chat",
            page.locator("#contact-list [data-companion]").count() == 10
            and page.locator(".message.user").count() == 0,
        )
        result["sampled_text_styles"] = page.evaluate(
            """() => ['.contact-snippet','.composer-note','.empty-conversation > p','.wordmark'].map(selector=>{const el=document.querySelector(selector),s=getComputedStyle(el);let bg=el;while(bg && ['rgba(0, 0, 0, 0)','transparent'].includes(getComputedStyle(bg).backgroundColor))bg=bg.parentElement;return {selector,foreground:s.color,background:bg?getComputedStyle(bg).backgroundColor:'rgb(255, 255, 255)',fontSize:s.fontSize};})"""
        )

        def luminance(color):
            rgb = [int(n) / 255 for n in re.findall(r"\d+", color)[:3]]
            linear = [
                n / 12.92 if n <= 0.04045 else ((n + 0.055) / 1.055) ** 2.4 for n in rgb
            ]
            return sum(
                n * w for n, w in zip(linear, (0.2126, 0.7152, 0.0722), strict=True)
            )

        for sample in result["sampled_text_styles"]:
            a, b = luminance(sample["foreground"]), luminance(sample["background"])
            sample["sampled_contrast_ratio"] = round(
                (max(a, b) + 0.05) / (min(a, b) + 0.05), 3
            )
        check(
            "sampled_selected_contact_text_contrast_at_least_4_5",
            result["sampled_text_styles"][0]["sampled_contrast_ratio"] >= 4.5,
            result["sampled_text_styles"][0],
        )
        result["contrast_scope"] = (
            "Four computed sRGB text/background samples only, not a full compositing, disabled-state, keyboard, zoom, screen-reader or WCAG acceptance audit."
        )
        page.screenshot(path=str(DEST / "desktop.png"), full_page=False)
        result["screenshots"].append("desktop.png")
        page.locator("#contact-search").fill("Talent")
        check(
            "desktop_search_filters_contacts",
            page.locator("#contact-list [data-companion]").count() == 1
            and "Talent Scout" in page.locator("#contact-list").inner_text(),
        )
        page.locator("#contact-search").fill("")
        page.locator('#contact-list [data-companion="talent"]').click()
        text = "Review the project-owned SQLite history contract. Synthetic browser smoke brief."
        page.locator("#brief-input").fill(text)
        page.locator("#brief-input").press("Control+Enter")
        check(
            "keyboard_saves_local_human_brief_only",
            page.locator(".message.user").inner_text() == text
            and "NOT AN AI RESPONSE" in page.locator(".message.system").inner_text(),
        )
        page.locator("#computer-settings").click()
        check(
            "computer_requirements_dialog_truthful",
            page.locator("#modal").is_visible()
            and "no VM or IDE session" in page.locator("#modal-body").inner_text(),
        )
        page.keyboard.press("Escape")
        check("escape_closes_dialog", not page.locator("#modal").is_visible())
        page.locator('[data-view="plugins"]').first.click()
        page.locator('button.tool-card[data-view="finance"]').click()
        page.locator("#finance-sample").click()
        page.locator("#finance-confirm").check()
        page.locator("#finance-analyze").click()
        check(
            "csv_requires_explicit_source_currency",
            bool(page.locator("#finance-error").inner_text())
            and page.locator(".finance-metrics").count() == 0,
        )
        page.locator("#finance-currency").select_option("USD")
        page.locator("#finance-confirm").check()
        page.locator("#finance-analyze").click()
        page.locator(".finance-metrics").wait_for(state="visible", timeout=3000)
        check(
            "fictional_csv_preview_remains_local_read_only",
            page.locator(".finance-metrics").count() == 1
            and "Read-only" in page.locator(".finance-boundary").inner_text(),
        )
        page.locator('.account-button[data-view="trust"]').click()
        check(
            "settings_labels_stale_packages_and_unwired_journal",
            "were not rebuilt for this OpenBot OS foundation"
            in page.locator("#main").inner_text()
            and "optional authenticated history API"
            in page.locator("#main").inner_text()
            and "not connected to this chat" in page.locator("#main").inner_text(),
        )
        context.close()
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=1,
            color_scheme="light",
            is_mobile=True,
            has_touch=True,
        )
        page = mobile.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on(
            "request", lambda r: requests.append({"method": r.method, "url": r.url})
        )
        page.goto(BASE, wait_until="networkidle")
        check(
            "mobile_starts_companion_list_not_thread",
            page.locator(".contact-panel").is_visible()
            and not page.locator(".conversation-panel").is_visible(),
        )
        page.screenshot(path=str(DEST / "mobile.png"), full_page=False)
        result["screenshots"].append("mobile.png")
        page.locator('#contact-list [data-companion="talent"]').click()
        check(
            "mobile_list_to_conversation_navigation",
            page.locator(".conversation-panel").is_visible()
            and not page.locator(".contact-panel").is_visible(),
        )
        page.locator("#show-computer").click()
        check(
            "mobile_details_disclose_no_real_pc",
            page.locator("#details-panel").is_visible()
            and "0 allocated PCs" in page.locator("#details-panel").inner_text(),
        )
        page.locator("#close-details").click()
        page.locator("#mobile-back").click()
        check(
            "mobile_back_restores_list",
            page.locator(".contact-panel").is_visible()
            and not page.locator(".conversation-panel").is_visible(),
        )
        page.set_viewport_size({"width": 320, "height": 640})
        check(
            "320px_list_has_no_horizontal_document_overflow",
            page.evaluate("document.documentElement.scrollWidth <= innerWidth"),
        )
        check("no_javascript_page_errors", not errors, errors)
        check(
            "no_external_application_requests",
            all(r["url"].startswith(BASE + "/") or r["url"] == BASE for r in requests),
            requests,
        )
        check(
            "no_privileged_network_writes",
            not any(r["method"] not in ["GET", "HEAD"] for r in requests),
            requests,
        )
        mobile.close()
        browser.close()
    result["status"] = "passed"
except Exception as e:
    result["status"] = "failed"
    result["failure_type"] = type(e).__name__
    result["failure"] = str(e)
    result["traceback"] = traceback.format_exc()
finally:
    result["passed_checks"] = sum(q["passed"] for q in checks)
    (DEST / "BROWSER_SMOKE.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))
if result["status"] != "passed":
    raise SystemExit(1)
