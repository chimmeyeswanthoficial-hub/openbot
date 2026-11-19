# OpenBot OS — license and distribution boundaries

The root `LICENSE` grants MIT rights in the original OpenBot OS code and
accompanying first-party documentation. The existing `work/LICENSE`,
`studio/LICENSE`, `control/LICENSE` and original author notices remain intact.
This does **not** relicense donor code, marks, OS runtimes, SDKs or local test
binaries. OpenBot OS is an independent project, not an official CopilotKit product.
No trademark clearance or endorsement is asserted.

## Retained components and notices

| Component | Source/notice | Boundary |
|---|---|---|
| CopilotKit/OpenBot selected reference source | `work/repos/OpenBot/LICENSE` (MIT) | Retained reference, not the currently installed backend. A different remote revision cannot retroactively remove this retained MIT grant. Do not silently replace it with a binary image. |
| CopilotKit SDK/runtime | Optional future pinned dependency; upstream MIT notices must accompany imported code | No SDK runner/Intelligence service integrated. Compatibility and package-specific audit required. |
| AG-UI official protocol contract | `work/third_party/ag-ui-contract/LICENSE`, `PROVENANCE.json`, exact spec 1.0 JSON schema | Actual MIT test-only schema adoption for CUSTOM-event validation, not a complete engine/transport. Optional JSON-schema test tools have their own locked permissive licenses; no product runtime dependency added. |
| OpenMuse finance selection | `studio/third_party/openmuse/LICENSE`, `PROVENANCE.json`, `OPENMUSE_ADOPTION.md` | Bounded MIT CSV adaptation; not all of OpenMuse/openfuse is integrated. |
| Bot HQ | `work/third_party/bot-hq/LICENSE`, `work/apps/bot-hq/` notices | MIT code with retained attribution; excluded donor artwork stays excluded. |
| Rakazo and OpenDots selected references | `work/third_party/donor-library/{rakazo,OpenDots}/LICENSE` | Their own notices apply. Private workspace recovery archives are not a product distribution. |
| findrepo and other retained tools | `work/tools/findrepo/LICENSE` and adjacent tool/source notices | A tool's license does not license any code that it discovers. |
| Windows WebView2 loader/SDK | `control/native/windows/WebView2-LICENSE.txt`, `control/releases/windows-x64/WebView2-LICENSE.txt` | Microsoft redistribution terms, **not** relicensed MIT. WebView2/Edge is an external runtime dependency of the historical Windows shell. |
| Historical Windows EXE and Android APK | `control/releases/` and `docs/openbot-os/NATIVE_BUILD_STATUS.md` | Existing unsigned/demo-key test artifacts; not a current OpenBot OS release. Native OS, SDK and WebView terms also apply. |

The distinct `nightly-labs/openbot` project uses **PolyForm Noncommercial 1.0.0**
at the reviewed pin. Its code has **not** been copied into this change. A
noncommercial restriction is not appropriate for this project's permissive OSS
core. Publicly observable product ideas do not authorize copying code or artwork.
The distinct historical `v0.1.11` resolves to
`e9cae2ac7c83936a6e7d22c820e9d7ec0726d880` with an independently verified Apache-2.0
LICENSE. That is only a historical intake candidate: no modules/NOTICE/dependencies
cleared or code integrated, and no permission for newer Noncommercial code.
See `evidence/openbot-os-history/NIGHTLY_LEGACY_LICENSE.json`.

## Meaning of the fully-open-source goal

All application code required for the intended **core** must be available under
OSI-approved licenses and buildable without a proprietary project backend,
mandatory cloud activation/license renewal, account or paid provider. History,
policy, approvals, persistence, queues and export must be project-owned, or use
explicitly audited OSS dependencies. The new conversation journal meets its
small standalone scope with Python's standard library and SQLite.

This is a design/release requirement, **not** a completed audit of every historic
file, transitive dependency or redistributable. Optional online models, Claude
Code/Antigravity/T3Code integrations, social platforms, proprietary operating
systems and their system WebViews retain their own terms. An MIT source license
does not make those external products open source. If an entirely OSS native
runtime stack is required too, the existing WebView2-dependent shell cannot be
counted as meeting it; choose and test an alternative separately.

## Before a distributable can be called compliant

1. Inventory all actual runtime/build dependencies and exact versions; attach
   SPDX/CycloneDX SBOMs, notices and complete corresponding source where required.
2. Reproduce the OSS core from an empty, credential-free environment with network
   blocked after approved dependencies are obtained; record every attempted egress.
3. Keep optional proprietary integrations outside core startup and document their
   terms, data destinations, consent and cost. Never include account tokens.
4. Review binary/SDK redistribution, font/artwork/mark rights and name availability.
5. Export only reviewed product files. The private complete workspace contains
   owner uploads, operating state and a dependency-based recovery vault: **do not
   publish or upload that entire workspace as a public source release.**

The name and MIT direction were requested by the owner. Human legal/distribution
review, credentials, signing, spending and release authorization remain human gates.
