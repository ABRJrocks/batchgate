# Security policy

## Reporting a vulnerability

Use the repository's private vulnerability reporting feature. Include the affected version, a minimal synthetic reproduction, and expected impact. Do not put secrets, real customer files, or private data in a public issue.

## Data handling

BatchGate 0.1.x reads local files. Validation makes no network calls, edits no source records, executes no user expressions, and imports no data into external systems. Installation can contact the configured package index for build tooling. Regular expressions come from trusted, reviewed contracts.

JSON, JUnit, HTML and console validation output omit cell values, raw input paths, key digests and numeric aggregate totals. Reports retain contract metadata, error codes, row locations, and counts. Field names and report titles are user-supplied metadata; keep them free of secrets. Review reports before sharing them.

Key checks use per-run HMAC digests in a private temporary directory. The directory is cleaned up on normal completion and handled exceptions. Abrupt process termination can leave temporary files; they contain keyed hashes and row metadata, not plaintext cells. This is not secure erasure or disk encryption. The operating system can still page memory to disk.

HTML reports have no JavaScript, external assets or network requests. Text metadata is escaped. JSON and XML serializers escape metadata for their formats. CLI report paths are checked against inputs and the contract. Python callers must supply `protected_paths` when writing reports. Output files are replaced atomically one at a time.

## Operational boundaries

Use an immutable data directory. File metadata snapshots detect ordinary mutation and replacement during validation; they do not lock files or defend against a malicious concurrent filesystem writer. Keep the same batch unchanged through the consuming task. Resolved symlink escapes are rejected, but the filesystem is not a sandbox against adversarial races.

Input bounds and bounded issue samples constrain normal workloads. A reviewed regex can still backtrack badly against a crafted string. Run untrusted batches with an outer execution timeout and appropriate memory/disk quotas in your orchestrator. No hard wall-clock timeout or disk quota is built in. SQLite disk use grows with key/reference volume.

A passing batch establishes only the declared properties of those scanned files. It does not prove provenance, absence of malware, regulatory compliance, semantic truth, financial settlement correctness, or compatibility with an undeclared consumer.

## Supported versions

The current 0.1.x prerelease line receives fixes while the contract stabilizes. No support SLA or production-readiness certification is offered.
