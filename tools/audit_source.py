#!/usr/bin/env python3
"""Audit public source, optional Git history and nested archives without printing matches."""
import argparse
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    'credential': re.compile(rb'(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,}|apikey_[A-Za-z0-9]{16,64}_[A-Za-z0-9]{32,128}|AKIA[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{20,})'),
    'private-key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'private-home': re.compile(rb'/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/|[A-Z]:\\Users\\[^\\\r\n]+\\'),
}


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def scan(data, location, findings, deny=()):
    for kind, pattern in PATTERNS.items():
        if pattern.search(data):
            findings.append({'file': location, 'reason': kind})
    if any(value.encode().lower() in data.lower() for value in deny):
        findings.append({'file': location, 'reason': 'release-specific private text'})


def filename(name, findings):
    path = PurePosixPath(name)
    if path.suffix in {'.p8', '.p12', '.pem', '.key', '.sqlite3', '.db'} or path.name.startswith('.env'):
        findings.append({'file': name, 'reason': 'secret/state file type'})


def archive(data, location, findings, deny=(), depth=0):
    if depth > 3:
        findings.append({'file': location, 'reason': 'excessive archive nesting'})
        return 0
    count = 0
    with zipfile.ZipFile(io.BytesIO(data)) as zipped:
        entries = zipped.infolist()
        if len(entries) > 1000 or sum(item.file_size for item in entries) > 80_000_000:
            findings.append({'file': location, 'reason': 'archive exceeds audit bounds'})
            return 0
        names = set()
        for item in entries:
            name = location + '!' + item.filename
            parts = PurePosixPath(item.filename)
            if (item.filename in names or parts.is_absolute() or '..' in parts.parts
                    or '\\' in item.filename or ':' in item.filename
                    or stat.S_ISLNK(item.external_attr >> 16)):
                findings.append({'file': name, 'reason': 'unsafe or duplicate archive entry'})
                continue
            names.add(item.filename)
            if item.is_dir():
                continue
            count += 1
            content = zipped.read(item)
            filename(name, findings)
            if item.filename.endswith(('.zip', '.pyz')):
                count += archive(content, name, findings, deny, depth + 1)
            else:
                scan(content, name, findings, deny)
    return count


def audit(history=False, artifacts=None, deny=()):
    findings = []
    files = [p.decode() for p in git('ls-files', '-z').split(b'\0') if p]
    for relative in files:
        path = ROOT / relative
        if path.is_symlink():
            findings.append({'file': relative, 'reason': 'tracked symlink needs explicit review'})
            continue
        filename(relative, findings)
        scan(path.read_bytes(), relative, findings, deny)
    commits = blobs = members = 0
    if history:
        for line in git('rev-list', '--objects', '--all').splitlines():
            oid, _, path = line.partition(b' ')
            kind = git('cat-file', '-t', oid.decode()).strip()
            data = git('cat-file', kind.decode(), oid.decode())
            location = oid.decode()[:12] + ':' + path.decode()
            if kind == b'blob':
                blobs += 1
                filename(path.decode(), findings)
                scan(data, location, findings, deny)
            elif kind == b'commit':
                commits += 1
                scan(data, location, findings, deny)
                for email in re.findall(rb'^(?:author|committer) .* <([^>]+)>', data, re.M):
                    if not email.endswith(b'@users.noreply.github.com'):
                        findings.append({'file': oid.decode()[:12], 'reason': 'commit email needs public disclosure review'})
    if artifacts:
        for path in sorted(Path(artifacts).iterdir()):
            if path.is_file() and path.suffix in {'.zip', '.pyz'}:
                members += archive(path.read_bytes(), path.name, findings, deny)
    return {'tracked_files': len(files), 'history_commits': commits, 'history_blobs': blobs,
            'archive_members': members, 'findings': findings,
            'scope': 'Recognizable patterns and paths; manual prose, metadata and license review is also required.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true')
    parser.add_argument('--artifacts', type=Path)
    parser.add_argument('--deny-text', action='append', default=[], help='Additional private text; matches are never printed')
    args = parser.parse_args()
    report = audit(args.history, args.artifacts, args.deny_text)
    print(json.dumps(report, indent=2))
    raise SystemExit(bool(report['findings']))
