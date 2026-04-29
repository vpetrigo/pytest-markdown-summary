from __future__ import annotations

import dataclasses

import pytest
from py_markdown_table.markdown_table import markdown_table


@dataclasses.dataclass(slots=True)
class _TestResult:
    count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    error_count: int = 0
    skip_count: int = 0
    xpass_count: int = 0
    xfail_count: int = 0


class _TestResultTracker:
    __slots__ = ("_tests",)

    def __init__(self) -> None:
        self._tests: dict[str, _TestResult] = {}

    @property
    def tests(self) -> dict[str, _TestResult]:
        return self._tests

    def reset(self) -> None:
        self._tests.clear()


_tracker = _TestResultTracker()


def _get_base_nodeid(item: pytest.Item) -> str:
    """Get the base node ID, stripping parametrize suffixes for grouping."""
    if item.originalname != item.name:
        # Parametrized test: reconstruct base nodeid from parent + original name
        return item.parent.nodeid + "::" + item.originalname
    return item.nodeid


def _escape_markdown(text: str) -> str:
    """Escape characters that could break markdown table formatting."""
    return text.replace("|", "\\|").replace("\n", " ")


def pytest_sessionstart(session: pytest.Session) -> None:
    _tracker.reset()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]):
    outcome = yield
    rep = outcome.get_result()
    nodeid = _get_base_nodeid(item)

    if nodeid not in _tracker.tests:
        _tracker.tests[nodeid] = _TestResult()

    node = _tracker.tests[nodeid]

    if rep.when in ("setup", "teardown"):
        if rep.outcome == "failed":
            node.count += 1
            node.error_count += 1
        elif rep.when == "setup" and rep.outcome == "skipped":
            node.count += 1
            node.skip_count += 1

    elif rep.when == "call":
        node.count += 1
        if hasattr(rep, "wasxfail"):
            # xfail-marked test
            if rep.outcome == "skipped":
                # Test failed as expected
                node.xfail_count += 1
            elif rep.outcome == "passed":
                # Test unexpectedly passed (non-strict xfail)
                node.xpass_count += 1
            elif rep.outcome == "failed":
                # Strict xfail: test passed but strict mode treats as failure
                node.xpass_count += 1
        else:
            if rep.outcome == "passed":
                node.pass_count += 1
            elif rep.outcome == "failed":
                node.fail_count += 1
            elif rep.outcome == "skipped":
                node.skip_count += 1


def result_row(name: str, result: _TestResult) -> dict[str, str]:
    fields = [
        "Name",
        "Passed",
        "Failed",
        "Errored",
        "Skipped",
        "Unexpectedly Passed",
        "Expectedly Failed",
        "Subtotal",
    ]
    map_to_attr = {
        "Passed": "pass_count",
        "Failed": "fail_count",
        "Errored": "error_count",
        "Skipped": "skip_count",
        "Unexpectedly Passed": "xpass_count",
        "Expectedly Failed": "xfail_count",
    }

    def make_count_str(count: int) -> str:
        return str(count) if count > 0 else ""

    result_dict: dict[str, str] = {}

    for field in fields:
        match field:
            case "Name":
                result_dict[field] = _escape_markdown(name)
            case "Subtotal":
                result_dict[field] = str(result.count)
            case _:
                result_dict[field] = make_count_str(getattr(result, map_to_attr[field]))

    return result_dict


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    md_content = []

    for test_id, node in _tracker.tests.items():
        md_content.append(result_row(test_id, node))

    if not md_content:
        return

    markdown = (
        markdown_table(md_content)
        .set_params(padding_width=3, padding_weight="centerleft", quote=False)
        .get_markdown()
    )

    print("\n\n" + markdown)
