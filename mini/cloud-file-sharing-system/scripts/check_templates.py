import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import app
from flask import render_template

TEMPLATES_DIR = ROOT / 'templates'
results = []

with app.test_request_context('/'):
    for p in sorted(TEMPLATES_DIR.glob('**/*.html')):
        rel = p.relative_to(TEMPLATES_DIR)
        name = str(rel).replace('\\', '/')
        try:
            html = render_template(name)
            results.append((name, 'ok', len(html)))
        except Exception as e:
            results.append((name, 'error', repr(e)))

for r in results:
    print(f"{r[0]:<40}  {r[1]:<6}  {r[2]}")

# Summary
errs = [r for r in results if r[1] != 'ok']
print('\nSummary:')
print(f'  Templates checked: {len(results)}')
print(f'  Errors: {len(errs)}')
if errs:
    print('\nErrors detail:')
    for e in errs:
        print(f'- {e[0]}: {e[2]}')
