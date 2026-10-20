"""Every operational route must keep its guard on the REAL handler in app.py.

A fixture that wraps a made-up route cannot notice a guard being removed from the real
one; removing @debug_route_required from /debug/test left the whole suite green.
"""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app.py"


def _routes():
    routes = []
    for node in ast.parse(APP.read_text()).body:
        if not isinstance(node, ast.FunctionDef):
            continue
        names = {d.id if isinstance(d, ast.Name) else getattr(d.func, "id", None) if isinstance(d, ast.Call) else None
                 for d in node.decorator_list}
        for d in node.decorator_list:
            if (isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "route"
                    and d.args and isinstance(d.args[0], ast.Constant)):
                routes.append((d.args[0].value, node.name, names))
    return routes


ROUTES = _routes()


def test_route_inventory_is_not_empty():
    assert len(ROUTES) > 50


@pytest.mark.parametrize("path, handler, guards",
                         [r for r in ROUTES if r[0].startswith("/debug/")], ids=lambda v: str(v))
def test_debug_routes_are_hidden_and_admin_only(path, handler, guards):
    assert "debug_route_required" in guards, f"{path} ({handler}) lost @debug_route_required"


@pytest.mark.parametrize("path, handler, guards",
                         [r for r in ROUTES if r[0].startswith("/cache/")], ids=lambda v: str(v))
def test_cache_routes_require_the_admin_secret(path, handler, guards):
    assert "admin_secret_required" in guards, f"{path} ({handler}) lost @admin_secret_required"


def test_expected_operational_routes_are_covered():
    paths = {r[0] for r in ROUTES}
    for required in ("/debug/test/<path:query>", "/cache/invalidate", "/cache/store", "/cache/prewarm",
                     "/cache/lookup", "/cache/analytics", "/cache/popular"):
        assert required in paths, f"{required} not found; update this guard test deliberately"


def test_no_handler_returns_raw_value_error_text():
    """Only reader-written messages may reach a response: PageRequestError and the
    verse parser's own wording. A broad `except ValueError` would also catch decoding
    and timestamp errors and send their text to the client."""
    import re
    source = APP.read_text()
    leaks = []
    for match in re.finditer(r"except ValueError as (\w+):\n(\s+)return jsonify\(\{[\"']error[\"']: str\(\1\)", source):
        preceding = source[max(0, match.start() - 200):match.start()]
        route = re.findall(r'@app\.route\(["\']([^"\']+)', source[:match.start()])[-1]
        # Suspended Iman routes 404 unless IMAN_ENABLED=1; re-check them before re-enabling.
        if "normalize_verse_query(" not in preceding and not route.startswith("/iman/"):
            leaks.append(source[:match.start()].count("\n") + 1)
    assert not leaks, f"broad ValueError text returned to clients at app.py lines {leaks}"
