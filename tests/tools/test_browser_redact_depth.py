"""Page-controlled JSON must not crash browser output redaction (#137067)."""

import json

import pytest

from agent.redact import REDACT_WALK_DEPTH_MARKER
from tools.browser_cdp_tool import _redact_cdp_output
from tools.browser_tool_snapshot import _redact_browser_output

SECRET = "sk-" + "a" * 30
WALKERS = [_redact_browser_output, _redact_cdp_output]


def _nest(leaf, levels: int, *, as_dict: bool):
    for _ in range(levels):
        leaf = {"x": leaf} if as_dict else [leaf]
    return leaf


@pytest.mark.parametrize("walker", WALKERS)
@pytest.mark.parametrize("as_dict", [False, True])
def test_hostile_deep_page_value_is_cut_off_not_raised(walker, as_dict):
    # Deeper than the interpreter recursion limit: RecursionError before the fix.
    redacted = walker(_nest(SECRET, 2_000, as_dict=as_dict))
    blob = json.dumps(redacted)
    assert SECRET not in blob
    assert REDACT_WALK_DEPTH_MARKER in blob


def _nested_json(leaf, levels: int, *, as_dict: bool) -> str:
    payload = json.dumps(leaf)
    for _ in range(levels):
        payload = '{"x":' + payload + '}' if as_dict else '[' + payload + ']'
    return payload


@pytest.mark.parametrize("walker", WALKERS)
def test_json_decoded_page_tree_reaches_the_bounded_walker(walker):
    """A normal JSON decode path preserves a Chrome-depth tree before redaction."""
    value = json.loads(_nested_json("hello", 300, as_dict=False))
    assert walker(value) == value
    # Chrome refuses DOM.getDocument past ~150 nested elements; each element is
    # node -> children[] -> node, so that is ~300 JSON levels and must survive whole.
    node = {"nodeId": 1, "nodeName": "#text", "nodeValue": "hello"}
    for i in range(150):
        node = {"nodeId": i + 2, "nodeName": "DIV", "children": [node]}
    assert walker(node) == node
