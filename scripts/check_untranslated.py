#!/usr/bin/env python
"""
Scan templates for hard-coded English text outside {% trans %} / {% blocktrans %}.
Reports potential untranslated strings (false-positives expected for dynamic content).

Usage: python scripts/check_untranslated.py [--strict]
"""
import re, sys, os
from pathlib import Path

ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = ROOT / "templates"

def check_file(filepath):
    content = Path(filepath).read_text(encoding='utf-8')
    clean = re.sub(r'\{%.*?%\}', '', content, flags=re.DOTALL)
    clean = re.sub(r'\{\{.*?\}\}', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<script.*?</script>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<!--.*?-->', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<[^>]+>', ' ', clean)
    words = re.findall(r'[a-zA-Z]{3,}(?:\s+[a-zA-Z]{2,})*', clean)
    issues = []
    skip = {'class', 'div', 'span', 'href', 'src', 'type', 'true', 'false',
            'none', 'null', 'with', 'for', 'if', 'endif', 'endfor',
            'load', 'block', 'endblock', 'extends', 'include', 'static',
            'csrf', 'token', 'url', 'var', 'let', 'const', 'function',
            'return', 'document', 'window', 'this', 'event', 'data'}
    for w in words:
        wl = w.lower().strip()
        if wl not in skip and len(wl) > 4 and not wl.startswith('http'):
            issues.append(w)
    return issues

total = 0
for tmpl in sorted(TEMPLATES_DIR.rglob('*.html')):
    rel = tmpl.relative_to(ROOT)
    issues = check_file(tmpl)
    if issues:
        if 'admin' not in str(rel):
            total += len(issues)
            if '--strict' in sys.argv:
                print(f"\n{rel}:")
                for i in issues[:10]:
                    print(f"  {i!r}")

if total and '--strict' in sys.argv:
    print(f"\n{total} potential untranslated strings found.")
    sys.exit(1)
else:
    print(f"check_untranslated: {total} potential strings (use --strict to see details)")
    sys.exit(0)
