// Pure reducer tests for the actual shared code imported by the built React client.
import test from 'node:test';
import assert from 'node:assert/strict';
import { clearRows, mergePage, mergeRows } from '../dist/history-state.js';

const row = (seq, rev = seq, generation = 1, text = `entry-${seq}`) => ({
  botId: 'fixture', generation, seq, updatedSeq: rev, kind: 'message',
  body: { type: 'message', role: 'user', text }, createdAt: seq,
});
const page = (rows, nextBeforeSeq = null, generation = 1, revision = Math.max(0, ...rows.map(r => r.updatedSeq))) =>
  ({ generation, revision, rows, hasMore: nextBeforeSeq !== null, nextBeforeSeq });
const keys = t => Object.keys(t.bySeq).map(Number).sort((a, b) => a - b);

test('earlier pages merge without duplicates and terminate at the first retained entry', () => {
  let state = mergePage(undefined, page([row(4), row(5)], 4));
  state = mergePage(state, page([row(2), row(3)], 2), 4);
  state = mergePage(state, page([row(1)], null), 2);
  assert.deepEqual(keys(state), [1, 2, 3, 4, 5]);
  assert.equal(state.nextBeforeSeq, null);
  assert.equal(state.loaded, true);
  assert.equal(state.loadingEarlier, false);
});

test('streamed edits outrank older page bodies and late older events', () => {
  let state = mergePage(undefined, page([row(4), row(5)], 4));
  state = mergeRows(state, 1, [row(3, 10, 1, 'streamed edit')]);
  state = mergePage(state, page([row(2), row(3)], 2), 4);
  state = mergeRows(state, 1, [row(3, 3)]);
  assert.equal(state.bySeq[3].body.text, 'streamed edit');
});

test('new snapshot keeps events arriving after its revision watermark', () => {
  const live = mergeRows(undefined, 1, [row(5, 10, 1, 'new edit'), row(6, 11)]);
  const state = mergePage(live, page([row(4), row(5)], 4, 1, 5));
  assert.deepEqual(keys(state), [4, 5, 6]);
  assert.equal(state.bySeq[5].body.text, 'new edit');
});

test('reconnect discards a gapped old window and offers a contiguous latest cursor', () => {
  const old = mergePage(undefined, page([row(1), row(2)], null));
  const state = mergePage(old, page([row(501), row(502)], 501));
  assert.deepEqual(keys(state), [501, 502]);
  assert.equal(state.nextBeforeSeq, 501);
});

test('late old-generation snapshots and pages cannot resurrect reset history', () => {
  const old = mergePage(undefined, page([row(4), row(5)], 4));
  const reset = clearRows(old, 2);
  assert.equal(mergePage(reset, page([row(1)])), reset);
  assert.equal(mergePage(reset, page([row(1)]), 4), reset);
  assert.equal(mergeRows(reset, 1, [row(6)]), reset);
  assert.deepEqual(keys(reset), []);
});

test('late clear events do not erase newer streamed rows or a newer generation', () => {
  const state = mergeRows(undefined, 2, [row(1, 12, 2)]);
  assert.equal(clearRows(state, 1), state);
  assert.equal(clearRows(state, 2), state);
  assert.deepEqual(keys(state), [1]);
});

test('out-of-order latest snapshots cannot roll back the latest accepted revision', () => {
  const state = mergePage(undefined, page([row(8), row(9)], 8));
  assert.equal(mergePage(state, page([row(4), row(5)], 4)), state);
});

test('duplicate or mismatched earlier responses cannot move the cursor or mix generations', () => {
  const state = mergePage(undefined, page([row(4), row(5)], 4));
  const next = mergePage(state, page([row(2), row(3)], 2), 4);
  assert.equal(mergePage(next, page([row(2), row(3)], 2), 4), next);
  assert.equal(mergePage(next, page([row(1, 1, 2)], null, 2), 2), next);
});

test('generation advance resets loading, stale cursors, errors and loaded claims', () => {
  const old = { ...mergePage(undefined, page([row(4)], 4)), loadingEarlier: true, historyError: 'old error' };
  const state = mergeRows(old, 2, [row(1, 9, 2), row(8, 8, 1)]);
  assert.deepEqual(keys(state), [1]);
  assert.equal(state.loaded, false);
  assert.equal(state.loadingEarlier, false);
  assert.equal(state.historyError, null);
  assert.equal(state.nextBeforeSeq, null);
});
