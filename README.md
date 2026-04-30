# pytest-markdown-summary

[![CI](https://github.com/vpetrigo/pytest-markdown-summary/actions/workflows/ci.yml/badge.svg)](https://github.com/vpetrigo/pytest-markdown-summary/actions/workflows/ci.yml)
![PyPI - Version](https://img.shields.io/pypi/v/pytest-markdown-summary)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pytest-markdown-summary)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/pytest-markdown-summary?period=monthly&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=GREEN&left_text=downloads%2Fmonth)](https://pepy.tech/projects/pytest-markdown-summary)

A [pytest](https://docs.pytest.org/) plugin that generates a Markdown summary table of your test results. Useful for CI
pipelines, pull request comments, and automated reporting.

-----

## Features

- Generates a clean Markdown table with per-test or per-file result breakdown
- Tracks all outcome types: passed, failed, errored, skipped, xfail, and xpass
- Groups parametrized test variants into a single row
- Includes a TOTAL summary row with aggregated counts
- Automatically creates output directories if they don't exist
- Zero configuration needed beyond specifying the output file path

## Installation

```bash
pip install pytest-markdown-summary
```

The plugin supports:

- Python: `>=3.11`
- pytest: `>=7,<10`

## Usage

The plugin is activated by providing the `--markdown-summary-file` option to pytest:

```bash
pytest --markdown-summary-file=report.md
```

### Command-Line Options

| Option                              | Description                                                                                             |
|-------------------------------------|---------------------------------------------------------------------------------------------------------|
| `--markdown-summary-file PATH`      | Path to the output Markdown report file. Report generation is disabled if not provided.                 |
| `--markdown-summary-use-test-names` | Track results per individual test function. When disabled (default), results are grouped per test file. |

### Per-File Grouping (Default)

By default, test results are grouped by file:

```bash
pytest --markdown-summary-file=report.md
```

### Per-Test Grouping

To track each test function individually:

```bash
pytest --markdown-summary-file=report.md --markdown-summary-use-test-names
```

## Output Example

### Per-File Mode (Default)

```bash
pytest --markdown-summary-file=report.md
```

| Test File          | Passed | Failed | Errored | Skipped | Unexpectedly Passed | Expectedly Failed | Subtotal |
|:-------------------|:------:|:------:|:-------:|:-------:|:-------------------:|:-----------------:|:--------:|
| tests/test_auth.py |   5    |        |         |    1    |                     |                   |    6     |
| tests/test_api.py  |   8    |   2    |         |         |                     |         1         |    11    |
| TOTAL              |   13   |   2    |         |    1    |                     |         1         |    17    |

### Per-Test Mode

```bash
pytest --markdown-summary-file=report.md --markdown-summary-use-test-names
```

| Test File          | Test Name        | Passed | Failed | Errored | Skipped | Unexpectedly Passed | Expectedly Failed | Subtotal |
|:-------------------|:-----------------|:------:|:------:|:-------:|:-------:|:-------------------:|:-----------------:|:--------:|
| tests/test_auth.py | test_login       |   3    |        |         |         |                     |                   |    3     |
| tests/test_auth.py | test_logout      |   1    |        |         |         |                     |                   |    1     |
| tests/test_api.py  | test_get_users   |   1    |        |         |         |                     |                   |    1     |
| tests/test_api.py  | test_create_user |        |   1    |         |         |                     |                   |    1     |
| TOTAL              |                  |   5    |   1    |         |         |                     |                   |    6     |

> **Note:** Parametrized tests (e.g., `@pytest.mark.parametrize`) are automatically grouped into a single row under the
> base test name.

## CI Integration

### GitHub Actions

Use the generated Markdown file in GitHub Actions job summaries:

```yaml
- name: Run tests
  run: pytest --markdown-summary-file=report.md

- name: Add summary to job
  if: always()
  run: cat report.md >> $GITHUB_STEP_SUMMARY
```

### As a PR Comment

You can also post the report as a pull request comment using actions
like [marocchino/sticky-pull-request-comment](https://github.com/marocchino/sticky-pull-request-comment):

```yaml
- name: Run tests
  run: pytest --markdown-summary-file=report.md

- name: Comment on PR
  if: always() && github.event_name == 'pull_request'
  uses: marocchino/sticky-pull-request-comment@v2
  with:
    path: report.md
```

## Contribution

Contributions are always welcome! If you have an idea, it's best to float it by me before working on it to ensure no
effort is wasted. If there's already an open issue for it, knock yourself out.

## License

<sup>
Licensed under <a href="LICENSE.md">MIT license</a>.
</sup>
