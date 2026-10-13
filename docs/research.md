# Research and scope

Reviewed on 13 October 2026. These sources establish useful validation patterns, not demand for this particular tool.

| Source | Design consequence |
| --- | --- |
| [Great Expectations uniqueness](https://docs.greatexpectations.io/docs/reference/learn/data_quality_use_cases/uniqueness/) | Check simple and composite keys before downstream joins and imports. |
| [Great Expectations integrity](https://docs.greatexpectations.io/docs/reference/learn/data_quality_use_cases/integrity/) | Validate relationships and the business result of transformations, not only field types. |
| [Frictionless Table Schema](https://specs.frictionlessdata.io/table-schema/) | Separate physical missing-value tokens from typed constraints, and make key semantics explicit. |
| [Frictionless validation](https://framework.frictionlessdata.io/docs/guides/validating-data.html) | File and package validation is already a mature category. |
| [Soda checks](https://docs.soda.io/soda-documentation/soda-v3/sodacl-reference/metrics-and-checks) | Volume and reference checks belong alongside field validation. |
| [Python CSV reader](https://docs.python.org/3/library/csv.html) | Use the standard parser with explicit newline handling and strict mode, not string splitting. |
| [JSON Lines](https://jsonlines.org/) | Require UTF-8, one object per line for this application, no BOM, and reject blank lines. |

## Existing alternatives

Use Frictionless when interoperable Table Schema and broad file-format support matter. Use Great Expectations or Soda when you need warehouse integrations and a wider observability platform. BatchGate focuses on a local file boundary: a reviewed JSON contract, no runtime dependencies or network calls, disk-backed key checks, decimal totals, and reports that omit cell values.

The contract is BatchGate's own versioned format. It is not a Frictionless or JSON Schema implementation. No novelty, adoption, performance leadership, or market-size claim is made.

## Intended workflow

Receive an immutable batch in a local directory. Validate every declared dataset, then check references and reconciliation totals. An import or ETL orchestrator proceeds only on exit code zero. The tool never edits, repairs, quarantines, or uploads source data.

## Release boundaries

CSV and object-based JSONL only. No databases, cloud storage, automatic schema inference, anomaly learning, or hosted UI. Input files must remain unchanged until the consuming step finishes. Reconciliation assumes the contract author has aligned currency, units, scope, and business meaning.
