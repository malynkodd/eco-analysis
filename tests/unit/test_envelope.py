"""Unit tests for the standard response envelope."""
from __future__ import annotations

import json

from eco_common.envelope import (
    EnvelopeJSONResponse,
    ErrorPayload,
    PaginationMeta,
    _envelope_dict,
    _looks_like_envelope,
    error_response,
    paginate,
    request_id_ctx,
)


def test_looks_like_envelope_detects_full_shape():
    assert _looks_like_envelope({"data": 1, "error": None, "meta": {}})


def test_looks_like_envelope_rejects_partial():
    assert not _looks_like_envelope({"data": 1})
    assert not _looks_like_envelope([1, 2, 3])
    assert not _looks_like_envelope("scalar")


def test_envelope_response_wraps_raw_dict():
    resp = EnvelopeJSONResponse(content={"a": 1})
    body = json.loads(resp.body)
    assert body["data"] == {"a": 1}
    assert body["error"] is None
    assert "request_id" in body["meta"]
    assert "timestamp" in body["meta"]


def test_envelope_response_does_not_double_wrap():
    pre = {"data": [1], "error": None, "meta": {"request_id": "abc", "timestamp": "t"}}
    resp = EnvelopeJSONResponse(content=pre)
    body = json.loads(resp.body)
    assert body == pre


def test_envelope_propagates_request_id_ctx():
    token = request_id_ctx.set("rid-test-123")
    try:
        resp = EnvelopeJSONResponse(content={"x": 1})
        body = json.loads(resp.body)
        assert body["meta"]["request_id"] == "rid-test-123"
    finally:
        request_id_ctx.reset(token)


def test_paginate_emits_pagination_meta():
    resp = paginate(items=[1, 2, 3], page=2, limit=10, total=23)
    body = json.loads(resp.body)
    assert body["data"] == [1, 2, 3]
    assert body["meta"]["pagination"] == {
        "page": 2, "limit": 10, "total": 23, "pages": 3,
    }


def test_paginate_zero_total_yields_zero_pages():
    resp = paginate(items=[], page=1, limit=20, total=0)
    body = json.loads(resp.body)
    assert body["meta"]["pagination"]["pages"] == 0


def test_error_response_carries_code_message_details():
    resp = error_response(
        status_code=404, code="not_found",
        message="Project missing", details={"id": 7},
    )
    assert resp.status_code == 404
    body = json.loads(resp.body)
    assert body["data"] is None
    assert body["error"] == {
        "code": "not_found",
        "message": "Project missing",
        "details": {"id": 7},
    }


def test_envelope_dict_serialises_pydantic_models():
    err = ErrorPayload(code="x", message="y")
    pag = PaginationMeta(page=1, limit=10, total=5, pages=1)
    out = _envelope_dict(data=None, error=err, pagination=pag)
    assert out["error"]["code"] == "x"
    assert out["meta"]["pagination"]["pages"] == 1
