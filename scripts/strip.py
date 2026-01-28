
from __future__ import annotations

import argparse
import io
import os
import re
import sys
import time
from pathlib import Path
from typing import Iterable, Tuple

import tokenize

TS = time.strftime('%Y%m%d_%H%M%S')

HTML_COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)
CSS_COMMENT_RE = re.compile(r'/\*.*?\*/', re.DOTALL)


def find_files(root: Path, exts: Iterable[str]) -> Iterable[Path]:
    for ext in exts:
        pattern = f"**/*.{ext.lstrip('.')}"
        for p in root.glob(pattern):
            if p.is_file():
                yield p


def backup_file(p: Path) -> Path:
    bak = p.with_suffix(p.suffix + f'.bak.{TS}')
    p.replace(p)                      
    p.copy = None                            
                                    
    import shutil

    shutil.copy2(p, bak)
    return bak


def strip_py_comments(path: Path) -> Tuple[str, int]:
    """Return (new_source, removed_count)"""
    try:
        src = path.read_text(encoding='utf-8')
    except Exception:
                                        
        src = path.read_bytes().decode('utf-8', errors='replace')

    removed = 0
    try:
        tokens = []
                                                                  
        sio = io.StringIO(src)
        for tok in tokenize.generate_tokens(sio.readline):
            tok_type = tok.type
            tok_string = tok.string
            if tok_type == tokenize.COMMENT:
                # keep shebang and encoding comments at top
                                                                    
                if tok_string.startswith('#!') or 'coding' in tok_string:
                    tokens.append(tok)
                else:
                    removed += 1
                                        
                    continue
            else:
                tokens.append(tok)
        new_src = tokenize.untokenize(tokens)
        return new_src, removed
    except tokenize.TokenError as e:
                                                                              
        lines = []
        for line in src.splitlines(True):
            s = line.lstrip()
            if s.startswith('#') and not s.startswith('#!') and 'coding' not in s:
                removed += 1
                continue
                                                                                                    
            if '#' in line and '"' not in line and "'" not in line:
                parts = line.split('#', 1)
                line = parts[0].rstrip() + '\n'
                removed += 1
            lines.append(line)
        return ''.join(lines), removed


def strip_html_comments(text: str) -> Tuple[str, int]:
    found = HTML_COMMENT_RE.findall(text)
    new = HTML_COMMENT_RE.sub('', text)
    return new, len(found)


def strip_css_comments(text: str) -> Tuple[str, int]:
    found = CSS_COMMENT_RE.findall(text)
    new = CSS_COMMENT_RE.sub('', text)
    return new, len(found)


def process_file(path: Path, dry_run: bool = True, backup: bool = True, verbose: bool = False) -> Tuple[int, int]:
    """Process a single file. Returns (removed_comments_count, bytes_changed)
    bytes_changed is 0 if no change, >0 if file would be modified.
    """
    ext = path.suffix.lower().lstrip('.')
    removed = 0
    changed_bytes = 0

    if ext == 'py':
        new_src, removed = strip_py_comments(path)
        orig = path.read_text(encoding='utf-8', errors='replace')
        if new_src != orig:
            changed_bytes = len(new_src.encode('utf-8'))
            if not dry_run:
                if backup:
                    import shutil
                    bak = path.with_suffix(path.suffix + f'.bak.{TS}')
                    shutil.copy2(path, bak)
                path.write_text(new_src, encoding='utf-8')
    elif ext == 'html':
        t = path.read_text(encoding='utf-8', errors='replace')
        new_t, removed = strip_html_comments(t)
        if new_t != t:
            changed_bytes = len(new_t.encode('utf-8'))
            if not dry_run:
                if backup:
                    import shutil
                    bak = path.with_suffix(path.suffix + f'.bak.{TS}')
                    shutil.copy2(path, bak)
                path.write_text(new_t, encoding='utf-8')
    elif ext == 'css':
        t = path.read_text(encoding='utf-8', errors='replace')
        new_t, removed = strip_css_comments(t)
        if new_t != t:
            changed_bytes = len(new_t.encode('utf-8'))
            if not dry_run:
                if backup:
                    import shutil
                    bak = path.with_suffix(path.suffix + f'.bak.{TS}')
                    shutil.copy2(path, bak)
                path.write_text(new_t, encoding='utf-8')
    else:
        if verbose:
            print(f"Skipping unsupported extension: {path}")
        return 0, 0

    if verbose:
        print(f"{path}: removed_comments={removed} changed_bytes={changed_bytes}")
    return removed, changed_bytes


def main(argv=None):
    ap = argparse.ArgumentParser(description='Strip comments from .py/.html/.css files')
    ap.add_argument('--target', '-t', default='.', help='Target directory (default: current dir)')
    ap.add_argument('--ext', '-e', default='py,html,css', help='Comma-separated extensions to process')
    ap.add_argument('--no-backup', action='store_true', help="Do not create .bak backups")
    ap.add_argument('--dry-run', action='store_true', help='Do not modify files, only report')
    ap.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    ap.add_argument('--min-removed', type=int, default=0, help='Only report files with at least this many removed comments')

    args = ap.parse_args(argv)

    root = Path(args.target).resolve()
    exts = [x.strip().lstrip('.') for x in args.ext.split(',') if x.strip()]

    total_removed = 0
    total_changed = 0
    files_checked = 0
    files_changed = 0

    for p in find_files(root, exts):
        files_checked += 1
        removed, changed_bytes = process_file(p, dry_run=args.dry_run, backup=not args.no_backup, verbose=args.verbose)
        if removed >= args.min_removed and (removed or changed_bytes):
            files_changed += 1
        total_removed += removed
        total_changed += 1 if changed_bytes else 0

    print('--- Summary ---')
    print(f'Target: {root}')
    print(f'Extensions: {exts}')
    print(f'Files scanned: {files_checked}')
    print(f'Files with changes: {files_changed}')
    print(f'Total comments removed: {total_removed}')
    print(f'Files modified: {total_changed} (dry-run={args.dry_run})')


if __name__ == '__main__':
    main()
