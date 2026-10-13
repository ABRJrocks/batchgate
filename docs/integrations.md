# Integration recipes

## GitHub Actions

Place the validation gate immediately before the import step. This composite action requires Python 3.10+ on PATH. Pin a reviewed commit SHA for reproducible use; `v0.1.0` below is a convenient first-release example.

```yaml
name: Import data
on: [workflow_dispatch]
permissions:
  contents: read
jobs:
  import:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262
      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065
        with:
          python-version: '3.12'
      - uses: ABRJrocks/batchgate@v0.1.0
        with:
          contract: contracts/commerce.json
          data-directory: incoming/current
          report-prefix: reports/import
      - run: python scripts/import_batch.py incoming/current
      - uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        if: always()
        with:
          name: import-validation
          path: reports/
```

A rejected batch fails the action. Reports are still written for a normal validation failure. Configuration and I/O failures use exit code 2 and may have no report. The action installs from the checked-out action directory and does not send data to a service. Installation can contact the configured package index for build tooling.

The action takes paths through environment variables and quoted shell arguments. They are never interpolated as shell source. It creates no tokens, uploads no artifacts by itself, and does not alter the input files. Artifact publication is controlled by the caller's workflow.

## Shell, cron, containers and ETL jobs

Install the wheel into the environment used by your orchestrator, then gate the next command with `&&`:

```sh
batchgate check contracts/commerce.json --data-dir incoming/current \
  --json-report reports/import.json --junit reports/import.xml \
  --html-report reports/import.html \
  && python scripts/import_batch.py incoming/current
```

Use `batchgate lint contracts/commerce.json` to review a contract without reading data files. Use `--quiet` to suppress the console summary. An outer timeout belongs in the orchestrator; individual input limits are not a total execution-time guarantee.

| Exit | Meaning | Orchestrator behavior |
| --- | --- | --- |
| 0 | Contract linted or batch accepted | Proceed after a successful `check` |
| 1 | Data or reconciliation rejected | Block the consuming job and inspect reports |
| 2 | Configuration, output or local I/O failure | Block the consuming job and inspect stderr |
| 130 | Interrupted | Treat the validation as incomplete |

Keep the source directory immutable from validation through import. Metadata checks catch ordinary changes during the scan; they do not create a transaction across BatchGate and the importing application.

## Choosing a gate

For a CRM import, declare customer IDs and required contact columns, then check references from child files. For ETL, check producer schema, volume, and referential integrity before loading. For commerce exports, reconcile compatible monetary totals with a reviewed tolerance. For a flat JSONL AI dataset, use scalar field rules and identifiers; nested schema validation is outside this release.

A matching sum alone does not establish per-order settlement correctness. Add per-record constraints in your application or a dedicated grouped reconciliation system when that is the requirement.
