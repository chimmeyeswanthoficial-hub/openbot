# AG-UI official contract — bounded MIT test-only adoption

`schema-1.0.json` is an unchanged copy of `spec/1.0/schema.json` at
`3416b86da4b3288e87f827c7f2759a7fa18b5231`. `LICENSE` is the original MIT notice;
`PROVENANCE.json` pins bytes, SHA-256 and the matched Git-blob ID.

Used only to validate the namespaced CUSTOM event emitted by our authenticated
human-history API. The product does not import a full SDK/runner, start a model,
resolve remote schemas or treat an event as authority. Do not call this complete
AG-UI compliance. The chosen live transport/runtime is still a separate task.

Explicit optional validation tools are pinned by
`../../requirements.agui-test.lock.txt`; install only into an approved disposable
test environment alongside the existing handoff/control locks. They are not
installed by import or made mandatory core runtime dependencies.

Update only through a reviewed immutable pin/compatibility decision. Never edit
upstream schema bytes to make a product test green, drop the license or silently
accept a different protocol version. See `../../../docs/openbot-os/AUTHENTICATED_HISTORY.md`
from the repository guide (the path is shown here as text, not an automated installer).
