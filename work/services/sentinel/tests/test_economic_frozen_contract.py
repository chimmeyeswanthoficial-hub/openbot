"""Use the exact static facts from the unchanged-base arithmetic witness."""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest
from economic_fixtures import scope
from economic_repository import EconomicBook
from repository import Store

FIXTURE = Path(__file__).resolve().parents[2] / 'ledger/fixtures/arithmetic-contract.json'
CASES = json.loads(FIXTURE.read_text())


@pytest.fixture()
def book(tmp_path):
    store = Store(str(tmp_path / 'frozen.sqlite3'))
    instance = EconomicBook(store, experimental=True, clock=lambda: '2000-01-01T00:00:00+00:00')
    yield instance
    store._conn.close()


def ingest(book, events):
    for event in events:
        book.ingest(json.dumps(event).encode(), scope())


@pytest.mark.parametrize('order', list(itertools.permutations(range(3))))
def test_frozen_linked_sale_facts_count_100_not_300(book, order):
    ingest(book, [CASES['sales'][index] for index in order])
    assert book.summary(scope())['capture_minor'] == 10000
    assert book.summary(scope())['posting_count'] == 1


@pytest.mark.parametrize('order', [(0, 1), (1, 0)])
def test_frozen_cumulative_refund_facts_count_50_not_70(book, order):
    ingest(book, [CASES['sales'][0], *(CASES['refunds'][index] for index in order)])
    summary = book.summary(scope())
    assert summary['refund_minor'] == summary['net_captured_minor'] == 5000


def test_frozen_distinct_equal_price_sales_still_count_twice(book):
    ingest(book, CASES['distinct'])
    assert book.summary(scope())['capture_minor'] == 20000
    assert book.summary(scope())['posting_count'] == 2


def test_frozen_exact_notification_replay_has_one_effect(book):
    ingest(book, [CASES['sales'][0]] * 2)
    assert book.summary(scope())['capture_minor'] == 10000
    assert book.summary(scope())['posting_count'] == 1
