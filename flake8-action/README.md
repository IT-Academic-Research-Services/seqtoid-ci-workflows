<p align="center">
  <a href="https://github.com/julianwachholz/flake8-action/actions"><img alt="flake8-action status" src="https://github.com/julianwachholz/flake8-action/workflows/units-test/badge.svg"></a>
</p>

# flake8-action

Run flake8 on your Python code.

> **Maintained fork (thorvath-slower).** Forked from
> [`julianwachholz/flake8-action`](https://github.com/julianwachholz/flake8-action),
> which still ships `runs.using: node16` (past EOL — force-run on a newer Node and
> being removed from GitHub runners). This fork modernizes the runtime to `node24`
> so it keeps working after the 2026-09-16 Node-20 removal, without abandoning the
> action's PR-annotation features. Changes are intentionally **not** sent upstream.
> Consumers pin this fork by commit SHA. See CZID-204.

## Usage

Create a workflow file in your repository:

```yaml
name: Code Quality

on:
  push:
    paths:
      - "**.py"

jobs:
  lint:
    name: Python Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.9"
      - name: Run flake8
        uses: julianwachholz/flake8-action@v2
        with:
          checkName: "Python Lint"
          path: path/to/files
          plugins: flake8-spellcheck
          config: path/to/flake8.ini
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

See the [actions tab](https://github.com/julianwachholz/flake8-action/actions) for runs of this action! :rocket:
