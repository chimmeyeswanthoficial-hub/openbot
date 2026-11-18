#!/usr/bin/env python3
"""Embed reviewed local assets and the attributed CSV adapter in one offline HTML."""

import base64
import hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
web = root / "web"
style = (web / "styles.css").read_text()
script = "\n".join(
    (web / name).read_text()
    for name in ("finance-preview.js", "finance-workspace.js", "gateway-session.js", "app.js")
)
if "</script" in script.lower() or "</style" in style.lower():
    raise SystemExit("embedded asset delimiter refused")
digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
csp = (
    "default-src 'none'; script-src 'sha256-"
    + digest
    + "'; style-src 'unsafe-inline'; img-src data:; connect-src 'self'; "
    + "object-src 'none'; base-uri 'none'; form-action 'none'"
)
page = (web / "template.html").read_text()
for marker, value in [("__CSP__", csp), ("__STYLE__", style), ("__SCRIPT__", script)]:
    if page.count(marker) != 1:
        raise SystemExit("exact single template marker required: " + marker)
    page = page.replace(marker, value)
(web / "index.html").write_text(page)
# One UI source, byte-identical generated native/gateway payloads. No SDK/install.
control = root.parent / "control"
if control.is_dir():
    for target in (control / "web/index.html", control / "native/ios/OpenBotControl/index.html"):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page)
print("built web/index.html", len(page.encode()), "bytes; no downloads or dependencies")
