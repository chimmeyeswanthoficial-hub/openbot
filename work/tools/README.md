# Local tools and runtime limits

## Installed in this workspace

- `findrepo/`: owner's pinned MIT zero-dependency Node CLI/skill, with local public-by-default
  credential/cache/instruction-write patches. Entry: `bash scripts/findrepo.sh` from the project
  root. Tests: `make reuse-test`. Provenance: `audit/source-pins.json` and the skill LOCAL_POLICY.
- `packages/bot-hq-queue/`: selected MIT serial-queue module, executed in the same offline Node
  test gate. Not a running Bot HQ host or a connected Worker adapter.
- `.claude/skills/reverse-engineer-anything/`: pinned REA instructions + references, not its
  executable/MCP/providers. Ordinary complete-source analysis does not require REA.

No npm install, global instruction rewrite, hooks or paid integrations were performed. Imported
skills do not install the software/services their documentation describes.

## Toolchain evidence and limitations

Node 20.20.2 / npm 10.8.2 was available for this intake. It supports the selected findrepo/queue
modules, but not the full Bot HQ host's Node >=22 requirement or the reviewed REA engine range.
Neither full host was installed, built or run. No Docker/Bun runtime or model/payment account was
configured for this review.

`INSTALL_LOG.md` records the **historical** larger donor toolchain installation/typechecks. Those
binaries/caches are not retained in snapshots. Do not mistake historical checks for a current
runtime or reinstall latest binaries blindly. Provision only a justified, pinned, checksum-verified
runtime/provider in a separate disposable environment, review its hooks/permissions/licences, then
record the actual install/build/runtime results. No pipe-to-shell installers are part of this intake.
