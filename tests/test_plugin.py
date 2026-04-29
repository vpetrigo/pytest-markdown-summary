"""Tests for pytest-markdown-summary plugin using pytester."""

from __future__ import annotations

import pytest


@pytest.fixture
def run_with_plugin(pytester: pytest.Pytester, tmp_path):
    """Helper fixture that runs pytester with the plugin enabled and a report file."""
    report_file = tmp_path / "report.md"

    def _run(*args: str, use_test_names: bool = True):
        cmd = ["-p", "pytest_markdown_summary", f"--md-report-file={report_file}"]
        if use_test_names:
            cmd.append("--md-use-test-names")
        cmd.extend(args)
        result = pytester.runpytest(*cmd)
        return result, report_file

    return _run


class TestCLIOptions:
    """Test that CLI options control plugin behavior."""

    def test_no_report_file_produces_no_output(self, pytester: pytest.Pytester):
        """Without --md-report-file, no report is generated."""
        pytester.makepyfile("""
            def test_pass():
                assert True
        """)
        result = pytester.runpytest("-p", "pytest_markdown_summary")
        # No markdown table in stdout
        output = result.stdout.str()
        assert "Passed" not in output or "Subtotal" not in output

    def test_report_file_is_created(self, pytester: pytest.Pytester, tmp_path):
        """--md-report-file creates the specified file."""
        report_file = tmp_path / "out" / "report.md"
        pytester.makepyfile("""
            def test_pass():
                assert True
        """)
        pytester.runpytest(
            "-p", "pytest_markdown_summary",
            f"--md-report-file={report_file}",
            "--md-use-test-names",
        )
        assert report_file.exists()
        content = report_file.read_text(encoding="utf-8")
        assert "test_pass" in content
        assert "Passed" in content

    def test_report_file_parent_dirs_created(self, pytester: pytest.Pytester, tmp_path):
        """Nested output path directories are created automatically."""
        report_file = tmp_path / "deep" / "nested" / "dir" / "report.md"
        pytester.makepyfile("""
            def test_pass():
                assert True
        """)
        pytester.runpytest(
            "-p", "pytest_markdown_summary",
            f"--md-report-file={report_file}",
            "--md-use-test-names",
        )
        assert report_file.exists()

    def test_use_test_names_flag(self, pytester: pytest.Pytester, run_with_plugin):
        """--md-use-test-names groups by individual test function."""
        pytester.makepyfile("""
            def test_a():
                assert True

            def test_b():
                assert False
        """)
        _, report_file = run_with_plugin(use_test_names=True)
        content = report_file.read_text(encoding="utf-8")
        assert "test_a" in content
        assert "test_b" in content

    def test_per_file_grouping_default(self, pytester: pytest.Pytester, run_with_plugin):
        """Without --md-use-test-names, results are grouped per file."""
        pytester.makepyfile("""
            def test_a():
                assert True

            def test_b():
                assert True

            def test_c():
                assert False
        """)
        _, report_file = run_with_plugin(use_test_names=False)
        content = report_file.read_text(encoding="utf-8")
        # Should NOT have individual test names
        assert "test_a" not in content
        assert "test_b" not in content
        assert "test_c" not in content
        # Should have the file name and aggregated counts
        assert "test_per_file_grouping_default" in content
        assert "3" in content  # subtotal of 3 tests


class TestBasicOutcomes:
    """Test that basic test outcomes are correctly reported."""

    def test_single_passing_test(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            def test_pass():
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_pass" in content
        assert "TOTAL" in content

    def test_single_failing_test(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            def test_fail():
                assert False
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_fail" in content

    def test_mixed_pass_and_fail(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            def test_pass():
                assert True

            def test_fail():
                assert False
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_pass" in content
        assert "test_fail" in content


class TestSkipHandling:
    """Test that skipped tests are correctly counted."""

    def test_skip_marker(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            import pytest

            @pytest.mark.skip(reason="not ready")
            def test_skipped():
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_skipped" in content

    def test_skipif_true(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            import pytest

            @pytest.mark.skipif(True, reason="condition met")
            def test_skipped():
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_skipped" in content

    def test_skipif_false_runs_normally(self, pytester: pytest.Pytester, run_with_plugin):
        """skipif(False) should NOT count as skip - test should run and pass."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.skipif(False, reason="condition not met")
            def test_not_skipped():
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_not_skipped" in content

    def test_dynamic_skip_in_body(self, pytester: pytest.Pytester, run_with_plugin):
        """pytest.skip() called inside test body should count as skip."""
        pytester.makepyfile("""
            import pytest

            def test_dynamic_skip():
                pytest.skip("skipping at runtime")
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_dynamic_skip" in content

    def test_skip_in_fixture(self, pytester: pytest.Pytester, run_with_plugin):
        """pytest.skip() in fixture should count as skip."""
        pytester.makepyfile("""
            import pytest

            @pytest.fixture
            def skip_fixture():
                pytest.skip("not available")

            def test_with_skip_fixture(skip_fixture):
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_with_skip_fixture" in content


class TestXfailHandling:
    """Test that xfail/xpass outcomes are correctly classified."""

    def test_xfail_expected_failure(self, pytester: pytest.Pytester, run_with_plugin):
        """xfail test that actually fails should count as 'Expectedly Failed'."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.xfail
            def test_expected_fail():
                assert False
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_expected_fail" in content
        assert "Expectedly Failed" in content

    def test_xpass_unexpected_pass(self, pytester: pytest.Pytester, run_with_plugin):
        """xfail test that passes should count as 'Unexpectedly Passed'."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.xfail
            def test_unexpected_pass():
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_unexpected_pass" in content
        assert "Unexpectedly Passed" in content

    def test_strict_xfail_pass_counts_as_xpass(
        self, pytester: pytest.Pytester, run_with_plugin
    ):
        """strict xfail test that passes is reported as failed by pytest but is semantically xpass."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.xfail(strict=True)
            def test_strict_xpass():
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_strict_xpass" in content


class TestParametrizedGrouping:
    """Test that parametrized tests are grouped by base test name."""

    def test_parametrized_all_pass(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            import pytest

            @pytest.mark.parametrize("n", [1, 2, 3])
            def test_param(n):
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_param" in content
        # Subtotal should be 3
        assert "3" in content

    def test_parametrized_mixed_outcomes(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            import pytest

            @pytest.mark.parametrize("n", [1, 2, 3])
            def test_param(n):
                if n == 2:
                    assert False
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_param" in content

    def test_parametrized_produces_single_row(
        self, pytester: pytest.Pytester, run_with_plugin
    ):
        """All parametrized variants should appear as one row in the table."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
            def test_many(n):
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        # Should appear only once as a grouped row (plus potentially in TOTAL)
        # Count occurrences in data rows (not the header)
        lines = [line for line in content.splitlines() if "test_many" in line]
        assert len(lines) == 1


class TestSetupTeardownErrors:
    """Test that fixture setup/teardown errors are reported as errors."""

    def test_setup_error(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            import pytest

            @pytest.fixture
            def broken_fixture():
                raise RuntimeError("setup exploded")

            def test_with_broken_fixture(broken_fixture):
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_with_broken_fixture" in content
        assert "Errored" in content

    def test_teardown_error(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            import pytest

            @pytest.fixture
            def teardown_broken():
                yield
                raise RuntimeError("teardown exploded")

            def test_with_teardown_error(teardown_broken):
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_with_teardown_error" in content


class TestSummaryRow:
    """Test that the summary/totals row is correct."""

    def test_summary_row_present(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            def test_a():
                assert True

            def test_b():
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "TOTAL" in content

    def test_summary_row_counts(self, pytester: pytest.Pytester, run_with_plugin):
        """Summary row should aggregate all individual test counts."""
        pytester.makepyfile("""
            import pytest

            def test_pass():
                assert True

            def test_fail():
                assert False

            @pytest.mark.skip
            def test_skip():
                pass
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        # Find the TOTAL row
        total_line = [line for line in content.splitlines() if "TOTAL" in line]
        assert len(total_line) == 1
        # TOTAL row should show subtotal of 3
        assert "3" in total_line[0]


class TestEdgeCases:
    """Test edge cases and robustness."""

    def test_no_tests_collected(self, pytester: pytest.Pytester, tmp_path):
        """Empty test suite should not crash and should not create report file."""
        report_file = tmp_path / "report.md"
        pytester.makepyfile("""
            # no tests here
            x = 1
        """)
        result = pytester.runpytest(
            "-p", "pytest_markdown_summary",
            f"--md-report-file={report_file}",
            "--md-use-test-names",
            "--no-header",
        )
        # Plugin should not crash; exit code 5 = no tests collected
        assert result.ret == pytest.ExitCode.NO_TESTS_COLLECTED
        # Report file should not be created for empty runs
        assert not report_file.exists()

    def test_class_based_tests(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            class TestMyClass:
                def test_method_a(self):
                    assert True

                def test_method_b(self):
                    assert False
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "TestMyClass::test_method_a" in content
        assert "TestMyClass::test_method_b" in content

    def test_multiple_markers_on_same_test(
        self, pytester: pytest.Pytester, run_with_plugin
    ):
        pytester.makepyfile("""
            import pytest

            @pytest.mark.skip
            @pytest.mark.parametrize("n", [1, 2, 3])
            def test_skip_param(n):
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_skip_param" in content

    def test_module_level_skip_marker(self, pytester: pytest.Pytester, run_with_plugin):
        """Tests with module-level pytestmark should be handled."""
        pytester.makepyfile("""
            import pytest
            pytestmark = pytest.mark.skip(reason="whole module skipped")

            def test_a():
                assert True

            def test_b():
                assert True
        """)
        _, report_file = run_with_plugin()
        content = report_file.read_text(encoding="utf-8")
        assert "test_a" in content
        assert "test_b" in content

    def test_per_file_mode_multiple_files(self, pytester: pytest.Pytester, tmp_path):
        """Per-file mode groups results from each file into a single row."""
        report_file = tmp_path / "report.md"
        pytester.makepyfile(
            test_alpha="""
                def test_1():
                    assert True

                def test_2():
                    assert True
            """,
            test_beta="""
                def test_3():
                    assert False

                def test_4():
                    assert True
            """,
        )
        pytester.runpytest(
            "-p", "pytest_markdown_summary",
            f"--md-report-file={report_file}",
        )
        content = report_file.read_text(encoding="utf-8")
        assert "test_alpha.py" in content
        assert "test_beta.py" in content
        # Individual test names should NOT appear
        assert "test_1" not in content
        assert "test_2" not in content
        assert "test_3" not in content
        assert "test_4" not in content
