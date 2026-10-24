from collections import Counter
from fractions import Fraction
from itertools import product
from random import Random

import pytest

from tigrifes.machine import PAYOUTS, conditional_prizes, from_stops, simulate, simulate_participants, spin


def test_enumeration_of_all_125_outcomes():
    rounds = [from_stops(stops) for stops in product(range(5), repeat=3)]
    counts = Counter(r.prize for r in rounds)
    assert counts == {0: 120, 5: 1, 10: 1, 15: 1, 25: 1, 50: 1}
    assert Fraction(sum(r.prize for r in rounds), 125) == Fraction(84, 100)
    assert Fraction(sum(r.profit for r in rounds), 125) == Fraction(-16, 100)
    assert len({r.center for r in rounds}) == 125


@pytest.mark.parametrize("symbol,prize,stop", [(s, p, (i - 1) % 5) for i, (s, p) in enumerate(PAYOUTS.items())])
def test_each_winning_triple(symbol, prize, stop):
    result = from_stops((stop,) * 3)
    assert result.center == (symbol,) * 3
    assert result.prize == prize
    assert result.profit == prize - 1


def test_circular_window_and_losing_center():
    result = from_stops((4, 0, 1))
    assert result.board == (("E", "A", "B"), ("A", "B", "C"), ("B", "C", "D"))
    assert result.prize == 0
    assert result.profit == -1


@pytest.mark.parametrize("stops", [(0, 1), (0, -1, 0), (0, 5, 0), (True, 0, 0), (0.5, 0, 0)])
def test_invalid_stops(stops):
    with pytest.raises(ValueError):
        from_stops(stops)


def test_rng_reproducible_and_continuous():
    rng = Random(2026)
    first = [spin(rng) for _ in range(5)]
    second = [spin(rng) for _ in range(5)]
    assert first + second == simulate(10, 2026)
    assert first != second
    assert first != simulate(5, 42)


def test_conditionals_empty_group_is_not_estimable():
    rows = conditional_prizes([from_stops((0, 1, 2))] * 4)
    assert rows[0]["pairs"] == 3
    assert rows[0]["proportion"] == 0
    assert rows[1]["pairs"] == 0
    assert rows[1]["proportion"] is None
    assert all(row["proportion"] is None for row in conditional_prizes([]))


def test_participants_stop_without_replenishment():
    sessions = simulate_participants(Random(42), count=2, balance=1, limit=500)
    assert all(p["balance"] >= 0 for p in sessions)
    assert all(len(p["trajectory"]) == 501 for p in sessions)
    for p in sessions:
        if p["exhausted"]:
            assert p["trajectory"][p["rounds"]:] == [0] * (501 - p["rounds"])
    zero = simulate_participants(Random(42), count=1, balance=0)[0]
    assert zero["rounds"] == 0
    assert zero["exhausted"]
