#!/usr/bin/env python3
"""Embed reviewed local assets and the attributed CSV adapter in one offline HTML."""

import base64
import hashlib
from pathlib import Path


def _read_asset(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


root = Path(__file__).resolve().parents[1]
web = root / "web"
style = _read_asset(web / "styles.css")
script = "\n".join(
    _read_asset(web / name)
    for name in ("finance-preview.js", "finance-workspace.js", "gateway-session.js", "app.js")
)
if "</script" in script.lower() or "</style" in style.lower():
    raise SystemExit("embedded asset delimiter refused")
digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii")
csp = (
    "default-src 'none'; script-src 'sha256-"
    + digest
    + "'; style-src 'unsafe-inline'; img-src data:; connect-src 'self'; "
    + "object-src 'none'; base-uri 'none'; form-action 'none'"
)
page = _read_asset(web / "template.html")
for marker, value in [("__CSP__", csp), ("__STYLE__", style), ("__SCRIPT__", script)]:
    if page.count(marker) != 1:
        raise SystemExit("exact single template marker required: " + marker)
    page = page.replace(marker, value)
encoded_page = page.encode("utf-8")
(web / "index.html").write_bytes(encoded_page)
# One UI source, byte-identical generated native/gateway payloads. No SDK/install.
control = root.parent / "control"
if control.is_dir():
    for target in (control / "web/index.html", control / "native/ios/OpenBotControl/index.html"):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(encoded_page)
print("built web/index.html", len(encoded_page), "bytes; no downloads or dependencies")
