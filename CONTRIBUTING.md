# Contributing

Use synthetic data in issues, fixtures and reports. Include the smallest reproduction and the expected behavior. Contract changes must preserve unknown-field rejection, explicit null/type semantics, and redacted diagnostics.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

On Windows activate with `.venv\Scripts\Activate.ps1`. CI covers Linux on Python 3.10, 3.12 and 3.13, and macOS/Windows on Python 3.12. Package checks build a source distribution and wheel, install the wheel into a fresh environment, and run the tests and examples.

For a parser or rule change, add a test that passes valid data and rejects a meaningful invalid case. Include malformed input, partial scans and report redaction where applicable. Test the CLI exit code when user-visible behavior changes. Run `git diff --check` before submission.

Prefer the standard library. Avoid adding remote services, network fetches, arbitrary-expression evaluation or silent data repair to the validation path. Discuss changes to the versioned contract before implementation.
