"""Unit tests for the multi-criteria AHP calculator.

Verifies:
  * perfectly consistent matrices yield CR = 0 and the textbook 3-1/3 weights
  * Saaty validation rejects non-square / non-reciprocal / off-scale matrices
  * is_benefit cost criteria are inverted in the alternative ranking
  * principal eigenvalue equals the matrix dimension when fully consistent
"""
from __future__ import annotations

import math

import pytest

from tests.conftest import load_service

_mc = load_service("mc", "multi-criteria-service", ["schemas", "ahp"])
schemas = _mc["schemas"]
ahp = _mc["ahp"]

AHPInput = schemas.AHPInput
AHPValidationError = ahp.AHPValidationError
calculate_ahp = ahp.calculate_ahp


def _consistent_3x3() -> list[list[float]]:
    # Weights in proportion 6 : 3 : 1 → all pairwise ratios (2, 6, 3) land
    # exactly on Saaty's 1-9 scale, so CR = 0 and λ_max = n.
    return [
        [1.0, 2.0, 6.0],
        [1 / 2, 1.0, 3.0],
        [1 / 6, 1 / 3, 1.0],
    ]


def _alt(name: str, **scores: float) -> dict:
    return {"name": name, **scores}


def test_perfectly_consistent_matrix_has_cr_zero_and_lambda_equals_n():
    data = AHPInput(
        criteria=["a", "b", "c"],
        comparison_matrix=_consistent_3x3(),
        alternatives=[_alt("X", a=1, b=1, c=1)],
    )
    result = calculate_ahp(data)

    assert result.is_consistent
    assert math.isclose(result.consistency_ratio, 0.0, abs_tol=1e-6)
    assert math.isclose(result.lambda_max, 3.0, abs_tol=1e-6)
    assert math.isclose(sum(result.weights), 1.0, abs_tol=1e-9)


def test_consistent_matrix_recovers_expected_weight_ratios():
    data = AHPInput(
        criteria=["a", "b", "c"],
        comparison_matrix=_consistent_3x3(),
        alternatives=[_alt("X", a=1, b=1, c=1)],
    )
    weights = calculate_ahp(data).weights
    # Consistent matrix with ratio 6 : 3 : 1 -> weights normalised to 0.6 / 0.3 / 0.1
    expected = [0.6, 0.3, 0.1]
    for w, e in zip(weights, expected):
        assert math.isclose(w, e, abs_tol=1e-4)


def test_inconsistent_matrix_flags_cr_above_threshold():
    # Deliberately inconsistent: A 9× B, B 9× C, but A only 1× C.
    data = AHPInput(
        criteria=["a", "b", "c"],
        comparison_matrix=[
            [1.0, 9.0, 1.0],
            [1 / 9, 1.0, 9.0],
            [1.0, 1 / 9, 1.0],
        ],
        alternatives=[_alt("X", a=1, b=1, c=1)],
    )
    result = calculate_ahp(data)
    assert not result.is_consistent
    assert result.consistency_ratio > 0.1


def test_non_reciprocal_matrix_rejected():
    data = AHPInput(
        criteria=["a", "b"],
        comparison_matrix=[[1.0, 3.0], [0.5, 1.0]],  # 0.5 ≠ 1/3
        alternatives=[_alt("X", a=1, b=1)],
    )
    with pytest.raises(AHPValidationError):
        calculate_ahp(data)


def test_off_saaty_scale_rejected():
    data = AHPInput(
        criteria=["a", "b"],
        comparison_matrix=[[1.0, 2.5], [0.4, 1.0]],  # 2.5 not on 1-9 scale
        alternatives=[_alt("X", a=1, b=1)],
    )
    with pytest.raises(AHPValidationError):
        calculate_ahp(data)


def test_diagonal_must_be_one():
    data = AHPInput(
        criteria=["a", "b"],
        comparison_matrix=[[2.0, 1.0], [1.0, 1.0]],
        alternatives=[_alt("X", a=1, b=1)],
    )
    with pytest.raises(AHPValidationError):
        calculate_ahp(data)


def test_cost_criterion_inverts_ranking():
    data = AHPInput(
        criteria=["benefit", "cost"],
        comparison_matrix=[[1.0, 1.0], [1.0, 1.0]],
        alternatives=[
            _alt("Cheap", benefit=10, cost=1),
            _alt("Pricey", benefit=10, cost=100),
        ],
        is_benefit=[True, False],
    )
    ranking = calculate_ahp(data).ranking
    by_name = {r["name"]: r for r in ranking}
    assert by_name["Cheap"]["rank"] < by_name["Pricey"]["rank"]


def test_is_benefit_length_must_match_criteria():
    data = AHPInput(
        criteria=["a", "b"],
        comparison_matrix=[[1.0, 1.0], [1.0, 1.0]],
        alternatives=[_alt("X", a=1, b=1)],
        is_benefit=[True],  # wrong length
    )
    with pytest.raises(AHPValidationError):
        calculate_ahp(data)


def test_ranking_is_dense_and_descending():
    data = AHPInput(
        criteria=["a", "b"],
        comparison_matrix=[[1.0, 3.0], [1 / 3, 1.0]],
        alternatives=[
            _alt("Low",  a=1, b=1),
            _alt("Mid",  a=2, b=2),
            _alt("High", a=4, b=3),
        ],
    )
    ranking = calculate_ahp(data).ranking
    assert [r["rank"] for r in ranking] == [1, 2, 3]
    assert ranking[0]["score"] >= ranking[1]["score"] >= ranking[2]["score"]
