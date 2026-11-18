# Source-only does not mean tool-free kernel tests

The shared Studio's 48 standard-library tests do not need these prerequisites. The
preserved kernel regression suite also exercises real namespace/media code and
worker preflight. Removing runtime state and tools is deliberately fail-closed;
a bare `pytest` can fail, not merely skip, when those mandatory fixtures are absent.
Do not weaken tests or silently fall back to host binaries to manufacture green.

## Disposable local profile

Use a fresh **test copy of the entire workspace**, never an operating company's
state. Keep `control/` beside `work/`: gateway tests bind the actual shared client
from `../control/web/index.html`. Copying only `work/` is an incomplete test layout.
No real account, provider, VM, business budget, grant or pilot record is needed.

1. Select the reviewed Python environment from `work/requirements.*.lock.txt`.
   Installs/lock refreshes are separate explicit operator actions. No virtualenv
   or third-party package cache is inside the source ZIP.
2. In that disposable source copy only, create the missing synthetic test-state
   inputs (the tool refuses any existing state directory and starts no services):

   ```sh
   python3 tools/prepare-test-state.py --work-root work --for-local-tests
   ```

   The two fixture files are marked non-operating and allow zero automatic spending.
   Their illustrative caps are test inputs, not approved spending or real balances.
   Never use them to run an operating worker/server. They are not a pilot ledger.
3. Review `work/scripts/bootstrap-isolation.py` and `work/audit/isolation-runtime-lock.json`.
   The locked mode-0755 Bubblewrap file must be present in that work copy's excluded
   cache even for exact-binding preparation tests. Its presence does not prove a VM.
   The existing explicit `--install` path is a separate reviewed download/extraction,
   not an action performed by source verification or Studio startup.
4. Review `work/scripts/bootstrap-owned-media.py`. Media tests need a real hash-locked
   FFmpeg / FFprobe receipt and matching library path. This Debian x86_64 setup is
   host-specific and GPL-enabled; no FFmpeg binary is redistributed in this source
   handoff. Explicitly select `MEDIA_TOOL_LOCK` and `MEDIA_LIBRARY_PATH` from that
   reviewed local receipt. No automatic PATH fallback or fake playable media exists.
5. Keep `OPENBOT_TEST_POSTGRES_DSN` and `OPENBOT_TEST_POSTGRES_ALLOW_WRITES` unset
   unless you have separately created a NEW owned disposable PostgreSQL profile.
   See `work/POSTGRES_PROFILE.md` before opting in to those administrative/write tests.
   Keep other production DSNs/credentials unset. Namespace integration cases additionally
   require explicit `OPENBOT_TEST_NAMESPACE=1` and a usable reviewed environment.
6. Run from `work/`, directing JUnit to a new test-evidence path outside source:

   ```sh
   python3 -m pytest --junitxml=/an/operator-chosen/new/evidence.xml
   ```

Any optional cases not run must remain skips, not passes. These fixtures test local
engineering only. External security, live providers, witnessed recovery, independent
evaluation, real elapsed pilot observations, native signing and human release remain
separate. Source manifests never include generated test-state directories or tools.

The observed handoff evidence retains the initial collection/setup failures as well
as the completed configured run. A source-only default failure is not relabelled as
a full 1424-pass result from the earlier, fully provisioned S11–S12 environment.
