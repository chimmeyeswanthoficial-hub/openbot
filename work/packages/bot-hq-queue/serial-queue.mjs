// Adapted from Bot HQ server/src/agent/loop.ts, runInBotQueue.
// Copyright (c) 2026 Nick Vasilescu; MIT. See ../../third_party/bot-hq/LICENSE.
// Upstream: decf9a215cddd8792a5f20f4a11a87d4dffa6d15.
// Local changes: dependency-free factory, explicit validation and close-to-new-work control.
// This is process-local serialization, NOT security isolation, durable jobs or remote cancellation.

export function createBotQueue() {
  const queues = new Map();
  let closed = false;

  function run(botId, job) {
    if (closed) return Promise.reject(new Error('queue closed to new work'));
    if (typeof botId !== 'string' || !botId.trim() || typeof job !== 'function') {
      return Promise.reject(new TypeError('a nonempty botId and job function are required'));
    }
    const prev = queues.get(botId) ?? Promise.resolve();
    const result = prev.then(job);
    // Preserve failure for the caller, but let the next job run after a failed predecessor.
    const next = result.then(() => {}, () => {});
    queues.set(botId, next);
    next.finally(() => { if (queues.get(botId) === next) queues.delete(botId); });
    return result;
  }

  return Object.freeze({
    run,
    isBusy: botId => queues.has(botId),
    close: () => { closed = true; }, // does not kill a tool/provider that is already running
    drain: async () => { await Promise.all([...queues.values()]); },
  });
}
