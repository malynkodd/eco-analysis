"""Unit tests for the server-side orchestration plumbing.

The `/api/v1/projects/{id}/analyze/full` endpoint relies on two pieces
we can verify in isolation without standing up every downstream service:

  * `eco_common.internal._unwrap` — must transparently peel the standard
    `{data, error, meta}` envelope and pass raw payloads through unchanged.
  * `FullAnalysisRequest` — must reject unknown fuel types and clamp the
    numeric bounds specified in the TS.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from eco_common.internal import _unwrap
from tests.conftest import load_service

_proj = load_service("proj", "project-service", ["schemas"])
FullAnalysisRequest = _proj["schemas"].FullAnalysisRequest


def test_unwrap_peels_envelope() -> None:
    enveloped = {
        "data": {"results": [1, 2, 3]},
        "error": None,
        "meta": {"request_id": "abc"},
    }
    assert _unwrap(enveloped) == {"results": [1, 2, 3]}


def test_unwrap_passes_non_envelope_through() -> None:
    assert _unwrap({"results": [1, 2, 3]}) == {"results": [1, 2, 3]}
    assert _unwrap([1, 2, 3]) == [1, 2, 3]
    assert _unwrap(None) is None


def test_full_analysis_defaults() -> None:
    req = FullAnalysisRequest()
    assert req.discount_rate == 0.1
    assert req.fuel_type == "electricity"
    assert req.sensitivity_variation_percent == 20.0


def test_full_analysis_rejects_unknown_fuel() -> None:
    with pytest.raises(ValidationError):
        FullAnalysisRequest(fuel_type="uranium")


def test_full_analysis_bounds() -> None:
    with pytest.raises(ValidationError):
        FullAnalysisRequest(sensitivity_variation_percent=0)
    with pytest.raises(ValidationError):
        FullAnalysisRequest(sensitivity_variation_percent=101)
    with pytest.raises(ValidationError):
        FullAnalysisRequest(discount_rate=-1.5)
