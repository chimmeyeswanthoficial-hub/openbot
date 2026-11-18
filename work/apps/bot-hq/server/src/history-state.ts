// OPENBOT-OS: pure client history state, based on Bot HQ's seq/revision merge in web/src/store.ts.
// MIT Bot HQ (c) 2026 Nick Vasilescu; new bounded page/reset handling is our local derivative.
import type { Row } from './types.js';

export interface RowsPage {
  generation: number;
  revision: number;
  rows: Row[];
  hasMore: boolean;
  nextBeforeSeq: number | null;
}
export interface Transcript {
  generation: number;
  bySeq: Record<number, Row>;
  loaded: boolean;
  nextBeforeSeq: number | null;
  loadingEarlier: boolean;
  historyError: string | null;
  snapshotRevision: number;
}
const empty = (generation: number): Transcript => ({
  generation, bySeq: {}, loaded: false, nextBeforeSeq: null,
  loadingEarlier: false, historyError: null, snapshotRevision: -1,
});

/** Ignore late events from an older conversation and older revisions of a streamed row. */
export function mergeRows(prev: Transcript | undefined, generation: number, rows: Row[]): Transcript {
  if (prev && generation < prev.generation) return prev;
  const base = !prev || generation > prev.generation ? empty(generation) : prev;
  const bySeq = { ...base.bySeq };
  for (const row of rows) {
    if (row.generation !== generation) continue;
    const cur = bySeq[row.seq];
    if (!cur || row.updatedSeq > cur.updatedSeq) bySeq[row.seq] = row;
  }
  return { ...base, bySeq };
}

/** A newer reset must not be undone by a delayed clear, snapshot or earlier-page response. */
export function clearRows(prev: Transcript | undefined, generation: number): Transcript {
  if (prev && generation <= prev.generation) return prev;
  return { ...empty(generation), loaded: true };
}

export function mergePage(prev: Transcript | undefined, page: RowsPage, beforeSeq?: number): Transcript | undefined {
  if (prev && page.generation < prev.generation) return prev;
  if (beforeSeq !== undefined) {
    if (!prev?.loaded || prev.generation !== page.generation || prev.nextBeforeSeq !== beforeSeq) return prev;
    return { ...mergeRows(prev, page.generation, page.rows), nextBeforeSeq: page.nextBeforeSeq,
      loadingEarlier: false, historyError: null };
  }
  if (prev?.generation === page.generation && prev.snapshotRevision > page.revision) return prev;
  // A reconnect uses a fresh contiguous latest window, not a union with possibly gapped old history.
  // Retain only events newer than the server's snapshot (ones arriving during the fetch).
  let next = mergeRows(undefined, page.generation, page.rows);
  if (prev?.generation === page.generation) {
    next = mergeRows(next, page.generation, Object.values(prev.bySeq).filter(row => row.updatedSeq > page.revision));
  }
  return { ...next, loaded: true, nextBeforeSeq: page.nextBeforeSeq, snapshotRevision: page.revision };
}
