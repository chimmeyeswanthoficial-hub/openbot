# Selected Bot HQ reuse — per-bot serial turns

An MIT-licensed port of `runInBotQueue` from
[`nickvasilescu/bot-hq@decf9a2`](https://github.com/nickvasilescu/bot-hq/blob/decf9a215cddd8792a5f20f4a11a87d4dffa6d15/server/src/agent/loop.ts).
See `third_party/bot-hq/LICENSE`, `THIRD_PARTY_NOTICES.md` and `queue-excerpt.ts.txt`.

`serial-queue.mjs` is installed as a local zero-dependency module and executed by its Node tests
(`make reuse-test`). This is a tested adapter building block, **not a running Bot HQ host** and
**not yet connected to Worker/OpenBot or any real model/tool**. No paid integration or artwork is
included. Node 18+ supports the extracted module; that does not satisfy the full Bot HQ host's
Node >=22 engine requirement or establish its build/runtime compatibility.

```js
import { createBotQueue } from './serial-queue.mjs';
const queue = createBotQueue();
await queue.run(trustedBotId, async () => {
  // The host must perform independent governance BEFORE each actual tool side effect.
  // Call an already-governed adapter here; do not expose raw shell/browser credentials.
});
queue.close(); // refuses NEW work only
await queue.drain();
```

Preserved semantics: one in-process job per bot at a time, parallelism across bots, failure reaches
its caller without poisoning later turns. Local additions: input validation, factory-scoped
state, close/drain. No restart durability, admission bound, hard provider cancellation, budget
reservation, tenant isolation or approvals. Add those at the execution boundary before live use.
Bot identity must come from authenticated server context, never a model-selected tenant ID.
