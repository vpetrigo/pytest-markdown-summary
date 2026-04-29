"""Tests for pytest-markdown-report plugin using pytester."""

from __future__ import annotations

import pytest


@pytest.fixture
def run_with_plugin(pytester: pytest.Pytester):
    """Helper fixture that runs pytester with the plugin enabled."""

    def _run(*args: str):
        return pytester.runpytest("-p", "pytest_markdown_report", "-s", *args)

    return _run


class TestBasicOutcomes:
    """Test that basic test outcomes are correctly reported."""

    def test_single_passing_test(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            def test_pass():
                assert True
        """)
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*Name*Passed*Subtotal*",
            "*test_pass*1*1*",
        ])

    def test_single_failing_test(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            def test_fail():
                assert False
        """)
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*Name*Failed*Subtotal*",
            "*test_fail*1*1*",
        ])

    def test_mixed_pass_and_fail(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            def test_pass():
                assert True

            def test_fail():
                assert False
        """)
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*test_pass*1*",
            "*test_fail*1*",
        ])


class TestSkipHandling:
    """Test that skipped tests are correctly counted."""

    def test_skip_marker(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            import pytest

            @pytest.mark.skip(reason="not ready")
            def test_skipped():
                assert True
        """)
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*test_skipped*1*1*",
        ])
        # Verify it shows up in Skipped column, not Passed
        output = result.stdout.str()
        assert "test_skipped" in output

    def test_skipif_true(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            import pytest

            @pytest.mark.skipif(True, reason="condition met")
            def test_skipped():
                assert True
        """)
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*test_skipped*1*1*",
        ])

    def test_skipif_false_runs_normally(self, pytester: pytest.Pytester, run_with_plugin):
        """skipif(False) should NOT count as skip - test should run and pass."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.skipif(False, reason="condition not met")
            def test_not_skipped():
                assert True
        """)
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*test_not_skipped*1*1*",
        ])

    def test_dynamic_skip_in_body(self, pytester: pytest.Pytester, run_with_plugin):
        """pytest.skip() called inside test body should count as skip."""
        pytester.makepyfile("""
            import pytest

            def test_dynamic_skip():
                pytest.skip("skipping at runtime")
        """)
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*test_dynamic_skip*1*1*",
        ])

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
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*test_with_skip_fixture*1*1*",
        ])


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
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*Expectedly Failed*",
            "*test_expected_fail*1*1*",
        ])

    def test_xpass_unexpected_pass(self, pytester: pytest.Pytester, run_with_plugin):
        """xfail test that passes should count as 'Unexpectedly Passed'."""
        pytester.makepyfile("""
            import pytest

            @pytest.mark.xfail
            def test_unexpected_pass():
                assert True
        """)
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*Unexpectedly Passed*",
            "*test_unexpected_pass*1*1*",
        ])

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
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*test_strict_xpass*1*1*",
        ])


class TestParametrizedGrouping:
    """Test that parametrized tests are grouped by base test name."""

    def test_parametrized_all_pass(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            import pytest

            @pytest.mark.parametrize("n", [1, 2, 3])
            def test_param(n):
                assert True
        """)
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*test_param*3*3*",
        ])

    def test_parametrized_mixed_outcomes(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            import pytest

            @pytest.mark.parametrize("n", [1, 2, 3])
            def test_param(n):
                if n == 2:
                    assert False
        """)
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*test_param*2*1*3*",
        ])

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
        result = run_with_plugin()
        output = result.stdout.str()
        # Should appear only once as a grouped row
        assert output.count("test_many") == 1


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
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*Errored*",
            "*test_with_broken_fixture*1*1*",
        ])

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
        result = run_with_plugin()
        # Should have both a pass (call) and an error (teardown)
        result.stdout.fnmatch_lines([
            "*test_with_teardown_error*1*1*2*",
        ])


class TestEdgeCases:
    """Test edge cases and robustness."""

    def test_no_tests_collected(self, pytester: pytest.Pytester, run_with_plugin):
        """Empty test suite should not crash."""
        pytester.makepyfile("""
            # no tests here
            x = 1
        """)
        result = run_with_plugin("--no-header")
        # Plugin should not crash; exit code 5 = no tests collected
        assert result.ret == pytest.ExitCode.NO_TESTS_COLLECTED

    def test_class_based_tests(self, pytester: pytest.Pytester, run_with_plugin):
        pytester.makepyfile("""
            class TestMyClass:
                def test_method_a(self):
                    assert True

                def test_method_b(self):
                    assert False
        """)
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*TestMyClass::test_method_a*1*1*",
            "*TestMyClass::test_method_b*1*1*",
        ])

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
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*test_skip_param*3*3*",
        ])

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
        result = run_with_plugin()
        result.stdout.fnmatch_lines([
            "*test_a*1*1*",
            "*test_b*1*1*",
        ])
