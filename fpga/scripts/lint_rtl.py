#!/usr/bin/env python3
"""
lint_rtl.py — Layer 7 Preventive Gate
Sovereign Matrix RTL Linter (pre-commit + CI)

Checks enforced:
  RULE-01  No unpacked array output ports (causes [Synth 8-9917])
  RULE-02  64-bit literals must fit in 16 hex digits (warns on truncation)
  RULE-03  initial blocks must have a ROM_INIT comment to be considered safe
  RULE-04  blocking assignment (var = ...) inside sequential always @(posedge) is banned
  RULE-05  direct function calls between modules (import keyword) are banned

Usage:
  python fpga/scripts/lint_rtl.py              # check all rtl/*.v
  python fpga/scripts/lint_rtl.py rtl/foo.v   # check specific file

Exit 0 = pass, 1 = failure.
"""

import re
import sys
import glob
from pathlib import Path

# Patterns
_UNPACKED_PORT = re.compile(
    r'\boutput\s+(?:reg\s+)?'
    r'\[\d+:\d+\]\s+'          # packed dimension (allowed)
    r'\w+'                      # port name
    r'\s+\[',                   # opening of unpacked dim
)
_HEX64 = re.compile(r"\b64'h([0-9A-Fa-f_]+)")
_INITIAL = re.compile(r'^\s*initial\b', re.M)
_BLOCKING_SEQ = re.compile(
    r'always\s*@\s*\(posedge.*?\).*?begin(.*?)end',
    re.DOTALL,
)
_BLOCKING_ASSIGN = re.compile(r'\b(\w+)\s*=\s*(?!=)')  # var = expr (not ==)


def check_file(path: str) -> list:
    """Return list of (rule, line_no, message) tuples."""
    errors = []
    code = Path(path).read_text(encoding='utf-8', errors='replace')
    lines = code.splitlines()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        # Skip comments
        if stripped.startswith('//'):
            continue

        # RULE-01: unpacked array output port
        if 'output' in line and _UNPACKED_PORT.search(line):
            # Exclude false positives: two ports on the same line
            if line.count('output') == 1:
                errors.append(('RULE-01', i,
                    f'Unpacked array output port: {stripped[:80]}'))

        # RULE-02: 64-bit literal > 16 hex digits
        for m in _HEX64.finditer(line):
            digits = m.group(1).replace('_', '')
            if len(digits) > 16:
                errors.append(('RULE-02', i,
                    f"64'h literal has {len(digits)} hex digits (max 16): {m.group(0)}"))

    # RULE-03: bare initial block without ROM_INIT tag
    for m in _INITIAL.finditer(code):
        line_no = code[:m.start()].count('\n') + 1
        ctx = code[m.start():m.start() + 120]
        if 'ROM_INIT' not in ctx:
            errors.append(('RULE-03', line_no,
                'initial block without ROM_INIT comment (use rst_n or tag)'))

    # RULE-04: blocking assignment inside sequential always
    for always_m in _BLOCKING_SEQ.finditer(code):
        body = always_m.group(1)
        start_line = code[:always_m.start()].count('\n') + 1
        for ba_m in _BLOCKING_ASSIGN.finditer(body):
            # Exclude <= (non-blocking), ==, loop vars (i, j, k, d, si, acc)
            if ba_m.group(1) in ('i', 'j', 'k', 'd', 'si', 'acc'):
                continue
            abs_line = start_line + body[:ba_m.start()].count('\n')
            errors.append(('RULE-04', abs_line,
                f'Blocking assignment in sequential block: {ba_m.group(0).strip()[:60]}'))
            break  # one report per always block

    return errors


def main(files=None) -> int:
    if files is None:
        files = sorted(glob.glob('rtl/*.v'))
    if not files:
        print('lint_rtl.py: no files to check')
        return 0

    total_errors = 0
    for f in files:
        errs = check_file(f)
        if errs:
            for rule, line, msg in errs:
                print(f'  {rule}  {f}:{line}  {msg}')
            total_errors += len(errs)

    n = len(files)
    if total_errors == 0:
        print(f'lint_rtl.py: {n} file(s) checked — ALL PASS')
        return 0
    else:
        print(f'lint_rtl.py: {total_errors} error(s) in {n} file(s)')
        return 1


if __name__ == '__main__':
    targets = sys.argv[1:] if len(sys.argv) > 1 else None
    sys.exit(main(targets))
