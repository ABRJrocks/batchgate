# Contract reference, version 1

BatchGate validates its own strict JSON format. Unknown fields, duplicate JSON object keys, non-finite numbers, contradictory bounds, invalid expressions, and unsupported versions fail before input files are read. `lint` validates only this contract. It does not assert that a batch exists or is valid.

## Top level

| Field | Meaning |
| --- | --- |
| `version` | Required integer `1` |
| `name` | Human-readable report title, 1 to 100 characters, no control characters |
| `datasets` | Required array of 1 to 100 datasets |
| `reconciliations` | Up to 50 named sum comparisons |
| `limits` | Optional scan and diagnostic bounds |

Dataset, field, and reconciliation identifiers match `[A-Za-z_][A-Za-z0-9_]{0,63}`. Dataset and reconciliation names must be unique. Keep sensitive information out of metadata, including field names and report titles.

## Dataset fields

| Field | Meaning |
| --- | --- |
| `name` | Required identifier |
| `path` | Required relative local file path under the selected data directory |
| `format` | `csv` or `jsonl` |
| `fields` | Required mapping of 1 to 200 field names to rules |
| `delimiter` | CSV delimiter, one character; default comma |
| `null_values` | Up to 50 CSV text tokens interpreted as null; default `[""]` |
| `allow_extra_fields` | Boolean; default false |
| `primary_key` | Nonempty array of 1 to 8 field names |
| `unique` | Up to 50 additional nonempty key arrays |
| `foreign_keys` | Up to 50 reference objects |
| `row_count` | Optional `min` and `max` record counts, inclusive |
| `comparisons` | Up to 50 field-pair comparisons |

Paths cannot be absolute, contain `..`, use backslashes, or name remote resources. Resolved inputs must remain inside the data directory and be regular files. Symlinks inside the root can work; escaping symlinks fail. Paths are resolved from `--data-dir`, or from the contract directory when that option is absent. No globbing, compression, network access, or format inference occurs.

CSV requires a nonempty unique header with at most 200 columns. Required columns must be present. Order is irrelevant. Extra columns fail unless explicitly allowed. Every record must have the same width as the header, including optional fields. UTF-8 with an optional BOM is accepted. Quoted multiline cells and CRLF files use Python's CSV reader in strict mode. The CLI uses Python's default CSV field-size limit, normally 128 KiB; library callers can change that process-wide setting.

JSONL requires UTF-8 without a BOM, one object per physical line. Blank lines, arrays, non-finite numbers, repeated object keys, and malformed JSON produce row errors. A malformed JSONL row does not hide later rows. Values can be nested in extra ignored fields; declared fields in this release must be scalars. A final newline is optional.

## Field rules

`type` is required. `required` defaults to true and controls whether a field must exist. `nullable` defaults to false and controls null values independently. Optional missing fields are skipped. JSONL null is only JSON `null`; CSV nulls use `null_values`. Empty JSON strings remain strings. No whitespace trimming, case folding, or Unicode normalization is performed.

| Type | Accepted values |
| --- | --- |
| `string` | Text, preserving identifiers such as `001` |
| `integer` | JSON integer tokens or strict CSV integer text; no booleans, decimal tokens, whitespace, leading plus or leading zeros |
| `decimal` | Finite JSON numbers or numeric strings, or strict CSV numeric text, using `Decimal`; no binary Python floats |
| `boolean` | JSON booleans or exact lowercase CSV `true` / `false` |
| `date` | Valid calendar date in `YYYY-MM-DD` form |
| `datetime` | `YYYY-MM-DDTHH:MM:SS` with optional 1 to 6 fractional digits and mandatory `Z` or `±HH:MM` offset; normalized to UTC |

Numeric values are limited to 1,000 textual characters and decimal exponents/adjusted exponents within ±1,000. Decimal sums use 4,096 digits of precision, enough for these input bounds and the row limit. Identifiers with formatting significance should be strings.

Optional constraints:

- `min`, `max`: inclusive integer/decimal bounds. Quote exact decimal bounds in JSON.
- `min_length`, `max_length`: inclusive string lengths in Unicode code points.
- `enum`: 1 to 100 values that parse as the declared type. Null is controlled by `nullable` separately.
- `pattern`: Python regular expression, full-string match, at most 1,000 pattern characters. Contracts must be reviewed and trusted. Use simple expressions and an outer task timeout.

A field reports its first failing constraint. Other fields, other rows, key checks, and relationships continue where parsing permits.

## Keys and references

Primary and unique key fields must be required and nonnullable. Duplicate definitions fail contract validation. Repeated keys produce `duplicate_key` issues on later occurrences. Composite keys preserve tuple boundaries. Exact string identity is used; decimals and UTC datetimes are normalized. A row with an invalid key field does not enter the key index. Other invalid fields do not prevent its otherwise valid key from participating.

A reference must target a declared primary or unique key with matching arity, field order, and types:

```json
{"fields": ["tenant", "customer_id"], "dataset": "customers", "references": ["tenant", "id"]}
```

References are checked after all files are scanned, so dataset order and cycles do not matter. If any source key component is null or missing, the reference is skipped, like SQL `MATCH SIMPLE`. Invalid source components also skip the reference but their field errors reject the batch. An unavailable or incomplete target produces `reference_unavailable`. A duplicate target key still rejects the whole batch even if membership succeeds.

Keys are stored as per-run HMAC-SHA256 digests in a private temporary SQLite directory. Plaintext key values are not written to the index. Key equality relies on the ordinary collision resistance assumption of the 256-bit hash. Disk use grows with rows, keys, and references; the tool does not impose a disk quota.

## Row comparisons

```json
{"left": "ordered_on", "op": "le", "right": "shipped_on"}
```

Supported operators: `lt`, `le`, `eq`, `ge`, `gt`. Both fields must be distinct and have the same nonboolean type. If either value is missing, null, or invalid, comparison is skipped. Declare required/nonnullable fields when the comparison must always run.

## Reconciliation

```json
{
  "name": "settlement",
  "left": {"dataset": "orders", "field": "amount"},
  "right": {"dataset": "payments", "field": "amount"},
  "tolerance": "0.01"
}
```

Each side is an integer/decimal column sum. Tolerance defaults to zero and must be finite and nonnegative. Null/optional missing values are omitted from sums when explicitly allowed. Empty datasets have zero totals; declare a minimum row count to guard missing batches. A reconciliation runs only if both involved datasets pass every dataset check. Otherwise it fails as `sum_unavailable`; a partial scan can never validate an aggregate.

These are whole-column totals. They do not group by currency, customer or order, evaluate arbitrary expressions, or convert units. Align business meaning in the contract and use additional checks when equal totals alone would be insufficient.

## Limits and results

| Limit | Default | Permitted range |
| --- | --- | --- |
| `max_rows` | 1,000,000 per dataset | 1 to 5,000,000 |
| `max_bytes` | 256 MiB per dataset | 1 to 2 GiB |
| `max_line_chars` | 1,048,576 including line terminators | 1 to 1,048,576 |
| `max_issues` | 200 samples per dataset | 0 to 10,000 |

A scan limit, decoding error, or fatal CSV parsing error makes the scan incomplete and rejects the batch. JSONL syntax and CSV width errors count as invalid rows. Samples stop at the configured cap, but issue counts and the rejection decision continue. `max_issues: 0` never disables validation. There is no allowed-error threshold; every detected issue is blocking.

Reports expose counts, scan completeness, known error codes, declared field identifiers, record numbers, and physical lines. An invalid row can have several issues, so issue count can exceed invalid-row count. A record's reported line is its final physical line. Fatal file and batch-level failures may have no row location. A complete scan means the parser reached the end; it does not mean the dataset passed.

Common codes include `type`, `null`, `missing_field`, `minimum`, `maximum`, `enum`, `pattern`, `min_length`, `max_length`, `comparison`, `duplicate_key`, `foreign_key`, `reference_unavailable`, `row_count`, `row_width`, `json_syntax`, `csv_syntax`, `invalid_header`, `missing_header`, `extra_header`, `extra_field`, `unreadable_file`, `file_changed`, `row_limit`, `byte_limit`, `line_limit`, `sum_match`, `sum_mismatch`, and `sum_unavailable`.
