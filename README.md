# FRC Snippet Check

Finds Java code examples in your Markdown docs (README, tutorials, team wiki) that use WPILib APIs which were removed, moved or deprecated, so students don't copy code that no longer compiles.

## Use it as a GitHub Action

```yaml
# .github/workflows/docs-check.yml
name: Check docs
on: [push, pull_request]
permissions:
  contents: read
jobs:
  snippets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Bonnie9981/FRC-Snippet-Check@main
        with:
          paths: docs README.md
          target-wpilib: 2026   # the season your docs are for
```

Problems show up as annotations on the file and line.

## Run it locally

```bash
python -m frc_snippet_check path/to/docs
```

Options: `--target-wpilib YEAR` (default 2026: APIs removed by that year are errors, deprecated ones are warnings, so 2024 docs can be checked with `--target-wpilib 2024`), `--only-tagged` (only check blocks opened with ```` ```java frc-check ````), `--fail-on error|warning|never`, `--format text|github|json`.

Skip a block with ```` ```java frc-check:skip ````, or one line with a `// frc-check:ignore` comment.

## Rules

The rules live in [`frc_snippet_check/rules.json`](frc_snippet_check/rules.json). Each one records the WPILib year it was deprecated and removed, with the line from the [WPILib yearly changelog](https://docs.wpilib.org/en/stable/docs/yearly-overview/yearly-changelog.html) it is based on (`"source"`); rules marked `unverified` only ever warn. They are regex checks, not a compiler, and comment lines are ignored. If a rule is wrong or missing, please open an issue.

Coming next: actually compiling tagged snippets against a chosen WPILib year.
