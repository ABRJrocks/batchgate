"""A self-contained accessible report with no scripts or remote assets."""
from html import escape


STYLE = '''
:root{color-scheme:light;--ink:#192c3c;--muted:#52616d;--line:#d5dde2;--paper:#fff;--page:#f3f5f6;--good:#166348;--bad:#9b3022}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--ink);font:16px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1160px;margin:48px auto;padding:0 24px}header{border-top:5px solid var(--ink);padding:24px 0}h1{font-size:clamp(28px,4vw,44px);line-height:1.15;margin:12px 0;overflow-wrap:anywhere}h2{font-size:23px;margin:0 0 16px}h3{font-size:19px}
p{margin:8px 0}.eyebrow{letter-spacing:.12em;text-transform:uppercase;font-size:12px;font-weight:700;color:var(--muted)}.status{font-weight:700}.pass{color:var(--good)}.fail{color:var(--bad)}.muted{color:var(--muted)}
.metrics{display:flex;flex-wrap:wrap;gap:32px;padding:22px 0;border-block:1px solid var(--line);margin:16px 0 32px}.metric strong{display:block;font-size:30px;line-height:1.2}.metric span{color:var(--muted);font-size:14px}
section{background:var(--paper);border:1px solid var(--line);padding:24px;margin:24px 0}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;text-align:left}caption{text-align:left;font-weight:600;margin-bottom:12px}th,td{padding:12px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}tr:last-child td{border-bottom:0}td,code{overflow-wrap:anywhere}code{font:13px ui-monospace,SFMono-Regular,monospace}details{border-top:1px solid var(--line);padding:16px 0}summary{cursor:pointer;font-weight:600}summary:focus-visible{outline:3px solid #285f91;outline-offset:4px}footer{font-size:13px;color:var(--muted);padding:20px 0 40px}a{color:#235984}
@media(max-width:600px){main{margin:16px auto;padding:0 12px}section{padding:16px}.metrics{gap:20px}th,td{padding:8px}}
@media print{body{background:white}main{margin:0;max-width:none;padding:0}section{break-inside:avoid}details{display:block}.table-wrap{overflow:visible}}
'''


def html_report(result):
    def status(passed):
        return '<span class="status pass">PASS</span>' if passed else '<span class="status fail">FAIL</span>'
    rows = sum(d.rows for d in result.datasets)
    invalid = sum(d.invalid_rows for d in result.datasets)
    issues = sum(d.issue_count for d in result.datasets)
    body = [f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>BatchGate | {escape(result.name)}</title><style>{STYLE}</style></head><body><main>
<header><div class="eyebrow">BatchGate / validation report</div><h1>{escape(result.name)}</h1>
<p>{status(result.passed)} <strong>{'Batch accepted' if result.passed else 'Batch rejected'}</strong></p>
<p class="muted">Local file validation. Source values and file paths are omitted.</p></header>
<div class="metrics" aria-label="Validation summary">
<div class="metric"><strong>{len(result.datasets)}</strong><span>datasets</span></div>
<div class="metric"><strong>{rows:,}</strong><span>rows scanned</span></div>
<div class="metric"><strong>{invalid:,}</strong><span>invalid rows</span></div>
<div class="metric"><strong>{issues:,}</strong><span>dataset issues</span></div></div>
<section><h2>Dataset checks</h2><div class="table-wrap"><table><caption>Batch integrity at a glance</caption>
<thead><tr><th scope="col">Dataset</th><th scope="col">Status</th><th scope="col">Scan</th><th scope="col">Rows</th><th scope="col">Invalid</th><th scope="col">Issues</th></tr></thead><tbody>''']
    for ds in result.datasets:
        body.append(f'<tr><th scope="row">{escape(ds.name)}</th><td>{status(ds.passed)}</td><td>{"Complete" if ds.complete else "Incomplete"}</td><td>{ds.rows:,}</td><td>{ds.invalid_rows:,}</td><td>{ds.issue_count:,}</td></tr>')
    body.append('</tbody></table></div></section>')
    if result.reconciliations:
        body.append('<section><h2>Reconciliation</h2><div class="table-wrap"><table><caption>Exact numeric totals within the declared tolerance</caption><thead><tr><th scope="col">Check</th><th scope="col">Status</th><th scope="col">Result</th></tr></thead><tbody>')
        for check in result.reconciliations:
            body.append(f'<tr><th scope="row">{escape(check.name)}</th><td>{status(check.passed)}</td><td><code>{escape(check.code)}</code></td></tr>')
        body.append('</tbody></table></div></section>')
    body.append('<section><h2>Diagnostics</h2><p class="muted">Rows are logical record numbers; lines identify the final physical line of a record. An invalid row can have several issues.</p>')
    for ds in result.datasets:
        if not ds.issue_count:
            continue
        body.append(f'<details open><summary>{escape(ds.name)}: {ds.issue_count:,} issues</summary><p>')
        body.append(' &middot; '.join(f'<code>{escape(code)}</code>: {count:,}' for code, count in sorted(ds.counts.items())))
        body.append('</p><div class="table-wrap"><table><caption>Bounded issue samples</caption><thead><tr><th scope="col">Code</th><th scope="col">Row</th><th scope="col">Line</th><th scope="col">Field</th></tr></thead><tbody>')
        for issue in ds.issues:
            body.append(f'<tr><td><code>{escape(issue.code)}</code></td><td>{issue.row if issue.row is not None else "Batch"}</td><td>{issue.line if issue.line is not None else ""}</td><td>{escape(issue.field or "")}</td></tr>')
        body.append(f'</tbody></table></div><p class="muted">{ds.issue_count - len(ds.issues):,} additional issues omitted from samples. Counts include every detected issue.</p></details>')
    if not issues:
        body.append('<p>No dataset issues were detected.</p>')
    body.append('</section><footer>BatchGate 0.1.1. A passing report covers the declared rules and the scanned files. Keep the batch immutable through the consuming step. This report contains contract metadata and row locations; review before sharing.</footer></main></body></html>\n')
    return ''.join(body)
