"""OpenAPI khai báo đúng query parameter và response lỗi của các endpoint list, và không lệch với API thật.

Danh sách param ở các test chống lệch được đọc từ schema OpenAPI do app sinh ra, không hard-code lại.
"""
from __future__ import annotations

from collections import Counter

import pytest

from app.config import DEFAULT_LIMIT, MAX_LIMIT

LIST_OPS = {
    "/api/v1/buildings/summary": {"start": True, "end": True, "building_id": False},
    "/api/v1/devices": {"building_id": False, "limit": False, "cursor": False},
    "/api/v1/devices/{device_id}/readings": {"metric": True, "start": True, "end": True, "limit": False, "cursor": False},
    "/api/v1/alerts": {"building_id": False, "device_id": False, "limit": False, "cursor": False},
}
UNKNOWN_PARAM_PREFIX = "tham số không được hỗ trợ"
# Giá trị hợp lệ theo seed/fixture (docs/testing/fixtures/mvp-normal.json) cho từng loại param.
SAMPLE_ID = {"building_id": "BLD-A", "device_id": "A-01"}
SAMPLE_TS = {"start": "2026-10-27T00:00:00Z", "end": "2026-10-27T00:03:00Z"}


@pytest.fixture()
def schema(client) -> dict:
    return client.app.openapi()


def _get_ops(schema: dict):
    for path, item in schema["paths"].items():
        if "get" in item:
            yield path, item["get"]


def _query_params(op: dict) -> list[dict]:
    return [p for p in op.get("parameters", []) if p["in"] == "query"]


def _sample(param: dict) -> str:
    name, s = param["name"], param["schema"]
    if "enum" in s:
        return s["enum"][0]
    if s.get("format") == "date-time":
        return SAMPLE_TS[name]
    if s["type"] == "integer":
        return str(s["default"])
    if name in SAMPLE_ID:
        return SAMPLE_ID[name]
    return "not-a-valid-cursor"


def _url(path: str, params: dict[str, str]) -> tuple[str, dict[str, str]]:
    return path.replace("{device_id}", SAMPLE_ID["device_id"]), params


def _is_unknown_param_error(resp) -> bool:
    if resp.status_code != 422:
        return False
    err = resp.json()["error"]
    return err["code"] == "INVALID_QUERY" and err["message"].startswith(UNKNOWN_PARAM_PREFIX)


def test_list_endpoints_declare_contract_query_parameters(schema):
    for path, expected in LIST_OPS.items():
        op = schema["paths"][path]["get"]
        declared = {p["name"]: p["required"] for p in _query_params(op)}
        assert declared == expected, path
        by_name = {p["name"]: p["schema"] for p in _query_params(op)}
        if "limit" in by_name:
            assert by_name["limit"] == {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT,
                                        "default": DEFAULT_LIMIT, "description": by_name["limit"]["description"]}
        if "metric" in by_name:
            assert by_name["metric"]["enum"] == ["power_kw", "energy_kwh"]
        for ts in ("start", "end"):
            if ts in by_name:
                assert by_name[ts]["format"] == "date-time" and by_name[ts]["pattern"].endswith("Z$")


def test_health_ready_declares_no_query_parameters(schema):
    assert _query_params(schema["paths"]["/api/v1/health/ready"]["get"]) == []


def test_list_endpoints_declare_500_internal_error(schema):
    for path in LIST_OPS:
        r500 = schema["paths"][path]["get"]["responses"]["500"]
        assert r500["description"] == "INTERNAL_ERROR"
        assert r500["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")


def test_readings_path_param_kept_and_no_duplicate_names_per_operation(schema):
    for path, op in _get_ops(schema):
        names = Counter(p["name"] for p in op.get("parameters", []))
        assert [n for n, c in names.items() if c > 1] == [], path
    readings = schema["paths"]["/api/v1/devices/{device_id}/readings"]["get"]["parameters"]
    path_params = [p for p in readings if p["in"] == "path"]
    assert [(p["name"], p["required"]) for p in path_params] == [("device_id", True)]


def test_every_declared_query_parameter_is_accepted_by_the_api(client, schema):
    checked = 0
    for path, op in _get_ops(schema):
        params = _query_params(op)
        required = {p["name"]: _sample(p) for p in params if p["required"]}
        for p in params:
            url, query = _url(path, {**required, p["name"]: _sample(p)})
            resp = client.get(url, params=query)
            assert not _is_unknown_param_error(resp), (path, p["name"], resp.json())
            if p["name"] == "cursor":
                # Được nhận diện là cursor và đi tới bước kiểm cursor, không phải bị từ chối vì tham số lạ.
                assert resp.status_code == 422 and resp.json()["error"]["code"] == "INVALID_CURSOR", (path, resp.json())
            else:
                assert resp.status_code == 200, (path, p["name"], resp.json())
            checked += 1
    assert checked == sum(len(v) for v in LIST_OPS.values())


def test_undeclared_query_parameter_is_still_rejected(client, schema):
    for path, op in _get_ops(schema):
        params = _query_params(op)
        declared = {p["name"] for p in params}
        undeclared = "zz_not_declared"
        assert undeclared not in declared
        required = {p["name"]: _sample(p) for p in params if p["required"]}
        url, query = _url(path, {**required, undeclared: "1"})
        resp = client.get(url, params=query)
        assert _is_unknown_param_error(resp), (path, resp.status_code, resp.json())


@pytest.mark.parametrize("query, message", [
    ({"lim": "10"}, "tham số không được hỗ trợ: lim"),
    ({"limit": "0"}, f"limit phải là số nguyên từ 1 đến {MAX_LIMIT}"),
    ({"limit": ["1", "2"]}, "tham số bị lặp: limit"),
])
def test_validation_behaviour_unchanged(client, query, message):
    resp = client.get("/api/v1/devices", params=query)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_QUERY"
    assert resp.json()["error"]["message"] == message
