"""Unit tests for the multi-criteria TOPSIS calculator."""

from __future__ import annotations

import math

import pytest

from tests.conftest import load_service

_mc = load_service("mc_topsis", "multi-criteria-service", ["schemas", "topsis"])
schemas = _mc["schemas"]
topsis = _mc["topsis"]

TOPSISInput = schemas.TOPSISInput
TOPSISValidationError = topsis.TOPSISValidationError
calculate_topsis = topsis.calculate_topsis


def _alt(name: str, **scores: float) -> dict:
    return {"name": name, **scores}


def test_dominant_alternative_wins():
    data = TOPSISInput(
        criteria=["benefit", "cost"],
        weights=[0.5, 0.5],
        is_benefit=[True, False],
        alternatives=[
            _alt("Worst", benefit=1, cost=10),
            _alt("Best", benefit=10, cost=1),
            _alt("Mid", benefit=5, cost=5),
        ],
    )
    ranking = calculate_topsis(data).ranking
    assert ranking[0]["name"] == "Best"
    assert ranking[-1]["name"] == "Worst"
    assert [r["rank"] for r in ranking] == [1, 2, 3]


def test_closeness_in_unit_interval():
    data = TOPSISInput(
        criteria=["a", "b", "c"],
        weights=[1.0, 2.0, 3.0],
        is_benefit=[True, True, True],
        alternatives=[
            _alt("X", a=1, b=2, c=3),
            _alt("Y", a=4, b=5, c=6),
            _alt("Z", a=7, b=8, c=9),
        ],
    )
    for r in calculate_topsis(data).ranking:
        assert 0.0 <= r["closeness_coefficient"] <= 1.0


def test_weights_normalised_to_sum_one():
    data = TOPSISInput(
        criteria=["a", "b"],
        weights=[3.0, 1.0],  # sum = 4
        is_benefit=[True, True],
        alternatives=[_alt("X", a=1, b=1), _alt("Y", a=2, b=2)],
    )
    weights = calculate_topsis(data).weights
    assert math.isclose(sum(weights), 1.0, abs_tol=1e-9)
    assert math.isclose(weights[0], 0.75, abs_tol=1e-6)


def test_weights_length_mismatch_rejected():
    data = TOPSISInput(
        criteria=["a", "b"],
        weights=[0.5],
        is_benefit=[True, True],
        alternatives=[_alt("X", a=1, b=1)],
    )
    with pytest.raises(TOPSISValidationError):
        calculate_topsis(data)


def test_zero_weight_sum_rejected():
    data = TOPSISInput(
        criteria=["a"],
        weights=[0.0],
        is_benefit=[True],
        alternatives=[_alt("X", a=1)],
    )
    with pytest.raises(TOPSISValidationError):
        calculate_topsis(data)


def test_missing_criterion_in_alternative_rejected():
    data = TOPSISInput(
        criteria=["a", "b"],
        weights=[0.5, 0.5],
        is_benefit=[True, True],
        alternatives=[_alt("X", a=1)],  # missing 'b'
    )
    with pytest.raises(TOPSISValidationError):
        calculate_topsis(data)


def test_cost_criterion_prefers_lower_value():
    data = TOPSISInput(
        criteria=["cost"],
        weights=[1.0],
        is_benefit=[False],
        alternatives=[
            _alt("Expensive", cost=100),
            _alt("Cheap", cost=1),
        ],
    )
    ranking = calculate_topsis(data).ranking
    assert ranking[0]["name"] == "Cheap"
