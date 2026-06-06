"""Tiny Flask-compatible fallback used in constrained test environments.

The production gateway pins Flask in requirements.txt. This module implements the
small subset of Flask APIs exercised by the gateway tests when dependencies
cannot be installed in the execution sandbox.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


class _Request:
    remote_addr = "127.0.0.1"
    _json: dict[str, Any] | None = None

    def get_json(self, silent: bool = False) -> dict[str, Any] | None:
        return self._json


request = _Request()


@dataclass
class Response:
    body: Any = None
    status_code: int = 200

    def get_json(self) -> Any:
        return self.body

    def get_data(self, as_text: bool = False) -> bytes | str:
        data = json.dumps(self.body) if self.body is not None else ""
        return data if as_text else data.encode()


def jsonify(obj: Any = None, **kwargs: Any) -> Response:
    return Response(kwargs if kwargs else obj, 200)


class Flask:
    def __init__(self, name: str) -> None:
        self.name = name
        self.config: dict[str, Any] = {}
        self._routes: list[tuple[str, str, Callable[..., Any]]] = []

    def route(self, path: str, methods: list[str] | tuple[str, ...] | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        methods = tuple(methods or ("GET",))

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            for method in methods:
                self._routes.append((method.upper(), path, func))
            return func

        return decorator

    def get(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route(path, methods=("GET",))

    def post(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route(path, methods=("POST",))

    def delete(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route(path, methods=("DELETE",))

    def test_client(self) -> "TestClient":
        return TestClient(self)

    def run(self, host: str = "127.0.0.1", port: int = 8080, threaded: bool = True, use_reloader: bool = False) -> None:
        raise RuntimeError("The lightweight Flask fallback does not implement a network server")

    def _dispatch(self, method: str, path: str, json_payload: dict[str, Any] | None = None, remote_addr: str = "127.0.0.1") -> Response:
        request._json = json_payload
        request.remote_addr = remote_addr
        for route_method, route_path, func in self._routes:
            params = _match(route_method, route_path, method.upper(), path)
            if params is None:
                continue
            result = func(**params)
            return _coerce_response(result)
        return Response({"error": "not found"}, 404)


def _match(route_method: str, route_path: str, method: str, path: str) -> dict[str, str] | None:
    if route_method != method:
        return None
    route_parts = route_path.strip("/").split("/") if route_path != "/" else []
    path_parts = path.strip("/").split("/") if path != "/" else []
    if len(route_parts) != len(path_parts):
        return None
    params: dict[str, str] = {}
    for route_part, path_part in zip(route_parts, path_parts):
        if route_part.startswith("<") and route_part.endswith(">"):
            params[route_part[1:-1]] = path_part
        elif route_part != path_part:
            return None
    return params


def _coerce_response(result: Any) -> Response:
    if isinstance(result, Response):
        return result
    if isinstance(result, tuple):
        body, status = result[0], result[1]
        response = body if isinstance(body, Response) else jsonify(body)
        response.status_code = status
        return response
    if isinstance(result, str):
        return Response(result, 200)
    return jsonify(result)


class TestClient:
    def __init__(self, app: Flask) -> None:
        self.app = app

    def get(self, path: str) -> Response:
        return self.app._dispatch("GET", path)

    def post(self, path: str, json: dict[str, Any] | None = None) -> Response:
        return self.app._dispatch("POST", path, json_payload=json)

    def delete(self, path: str) -> Response:
        return self.app._dispatch("DELETE", path)
