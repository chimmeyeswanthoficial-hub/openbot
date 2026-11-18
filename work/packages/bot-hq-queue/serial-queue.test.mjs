import test from 'node:test';
import assert from 'node:assert/strict';
import { createBotQueue } from './serial-queue.mjs';
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };

test('same bot executes one turn at a time, preserving order', async () => {
  const q = createBotQueue(), hold = deferred(), seen = [];
  const first = q.run('ops', async () => { seen.push(1); await hold.promise; seen.push(2); });
  const second = q.run('ops', () => { seen.push(3); return 'done'; });
  await Promise.resolve();
  assert.deepEqual(seen, [1]);
  assert.equal(q.isBusy('ops'), true);
  hold.resolve();
  await first;
  assert.equal(await second, 'done');
  await q.drain();
  assert.deepEqual(seen, [1, 2, 3]);
  assert.equal(q.isBusy('ops'), false);
});

test('different bots do not wait for one another', async () => {
  const q = createBotQueue(), hold = deferred();
  const first = q.run('ops', () => hold.promise);
  assert.equal(await q.run('audit', () => 'independent'), 'independent');
  assert.equal(q.isBusy('ops'), true);
  hold.resolve(); await first; await q.drain();
});

test('failure reaches caller but does not poison subsequent turns', async () => {
  const q = createBotQueue();
  const first = q.run('ops', () => { throw new Error('tool failed'); });
  const second = q.run('ops', () => 42);
  await assert.rejects(first, /tool failed/);
  assert.equal(await second, 42);
  await q.drain();
});

test('closing refuses new work but drains existing work without claiming cancellation', async () => {
  const q = createBotQueue(), hold = deferred();
  const first = q.run('ops', () => hold.promise);
  q.close();
  await assert.rejects(q.run('ops', () => 99), /closed/);
  hold.resolve('finished');
  assert.equal(await first, 'finished'); await q.drain();
});

test('invalid bot identity and callback are rejected', async () => {
  const q = createBotQueue();
  await assert.rejects(q.run('', () => {}), TypeError);
  await assert.rejects(q.run('ops', null), TypeError);
});
