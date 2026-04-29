from __future__ import annotations

import dataclasses
import pathlib
from typing import Self

import pytest
from py_markdown_table.markdown_table import markdown_table

_REPORT_FILE_OPTION = "--md-report-file"
_USE_TEST_NAMES_OPTION = "--md-use-test-names"


@dataclasses.dataclass(slots=True)
class _TestResult:
    count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    error_count: int = 0
    skip_count: int = 0
    xpass_count: int = 0
    xfail_count: int = 0

    def __iadd__(self, other: _TestResult) -> Self:
        self.count += other.count
        self.pass_count += other.pass_count
        self.fail_count += other.fail_count
        self.error_count += other.error_count
        self.skip_count += other.skip_count
        self.xpass_count += other.xpass_count
        self.xfail_count += other.xfail_count
        return self


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


def _get_file_nodeid(item: pytest.Item) -> str:
    """Get the file-level node ID for per-file grouping."""
    if item.path is not None:
        try:
            return str(item.path.relative_to(item.config.rootpath))
        except ValueError:
            return str(item.path)
    return item.nodeid


def _escape_markdown(text: str) -> str:
    """Escape characters that could break markdown table formatting."""
    return text.replace("|", "\\|").replace("\n", " ")


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("markdown-report", "Markdown report generation")
    group.addoption(
        _REPORT_FILE_OPTION,
        action="store",
        default=None,
        metavar="PATH",
        help="Path to the output Markdown report file. "
        "Report generation is disabled if not provided.",
    )
    group.addoption(
        _USE_TEST_NAMES_OPTION,
        action="store_true",
        default=False,
        help="Track results per individual test function. "
        "When disabled (default), results are grouped per test file.",
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    _tracker.reset()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]):
    outcome = yield
    report_file = item.config.getoption(_REPORT_FILE_OPTION)

    if report_file is None:
        return

    rep = outcome.get_result()
    use_test_names = item.config.getoption(_USE_TEST_NAMES_OPTION)
    nodeid = _get_base_nodeid(item) if use_test_names else _get_file_nodeid(item)

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
        elif rep.outcome == "passed":
            node.pass_count += 1
        elif rep.outcome == "failed":
            node.fail_count += 1
        elif rep.outcome == "skipped":
            node.skip_count += 1


def _result_row(name: str, result: _TestResult) -> dict[str, str]:
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


def _summary_row(total: _TestResult) -> dict[str, str]:
    """Build a summary/totals row for the bottom of the table."""
    return _result_row("TOTAL", total)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    report_file = session.config.getoption(_REPORT_FILE_OPTION)

    if report_file is None:
        return

    md_content = []
    total = _TestResult()

    for test_id, node in _tracker.tests.items():
        md_content.append(_result_row(test_id, node))
        total += node

    if not md_content:
        return

    md_content.append(_summary_row(total))

    markdown = (
        markdown_table(md_content)
        .set_params(padding_width=3, padding_weight="centerleft", quote=False)
        .get_markdown()
    )

    output_path = pathlib.Path(report_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
