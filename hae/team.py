"""Acquire reviewed upstream skill files, without executing or activating them.

Only repository paths and hashes ship with HAE. All bytes are staged and checked
before the installer receives them. Source snapshots and cached archives are
untrusted; no archive extraction is used.
"""
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import time
import urllib.error
import urllib.request
import zipfile
import zlib

from . import fs
from .packaging import resource

PREFIX = '.agents/skill-library/hae-team'
FILE_LIMIT = 16 * 1024 * 1024
TOTAL_LIMIT = 64 * 1024 * 1024
FILE_COUNT_LIMIT = 5000
ARCHIVE_LIMIT = 128 * 1024 * 1024
ARCHIVE_TOTAL_LIMIT = 512 * 1024 * 1024
ARCHIVE_COUNT_LIMIT = 50000
DOWNLOAD_SECONDS = 45
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'{p}{i}' for p in ['COM', 'LPT'] for i in range(1, 10))}


def _path(value):
    if not isinstance(value, str) or not value or len(value) > 1024 or '\\' in value:
        raise fs.Conflict('Unsafe team source path')
    parts = PurePosixPath(value).parts
    if (value.startswith('/') or '/'.join(parts) != value or any(
        p in {'.', '..'} or p.rstrip(' .') != p or ':' in p
        or any(c in '<>:"|?*' for c in p) or p.split('.')[0].upper() in RESERVED or any(ord(c) < 32 for c in p)
        for p in parts)):
        raise fs.Conflict('Unsafe team source path')
    return value


def manifest():
    """Return the pinned portable inventory, including license exclusions."""
    try:
        lock = json.loads(resource('team-skills.lock.json'))
        if lock['schema_version'] != 1 or lock['install_prefix'] != PREFIX:
            raise ValueError('schema')
        count = size = 0
        names = set()
        for repo in lock['repositories']:
            if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo['repository']):
                raise ValueError('repository')
            if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo['archive_repository']):
                raise ValueError('archive_repository')
            _path(repo['repository'])
            _path(repo['archive_repository'])
            _path(repo['slug'])
            if '/' in repo['slug'] or repo['slug'].casefold() in names:
                raise ValueError('slug')
            names.add(repo['slug'].casefold())
            if not re.fullmatch(r'[0-9a-f]{40}', repo['commit']):
                raise ValueError('commit')
            paths = set()
            for item in repo['files']:
                path = _path(item['path'])
                if path.casefold() in paths or not re.fullmatch(r'[0-9a-f]{64}', item['sha256']):
                    raise ValueError('file')
                paths.add(path.casefold())
                if type(item['size']) is not int or not 0 <= item['size'] <= FILE_LIMIT:
                    raise ValueError('size')
                count += 1
                size += item['size']
            for bundle in repo['bundles']:
                _path(bundle['path'])
                if _path(bundle['entry']).casefold() not in paths or type(bundle['eligible']) is not bool:
                    raise ValueError('bundle')
        if count > FILE_COUNT_LIMIT or size > TOTAL_LIMIT:
            raise ValueError('limits')
        return lock
    except (KeyError, TypeError, ValueError, UnicodeError):
        raise fs.Conflict('Invalid pinned team manifest') from None


def _eligible(repo):
    excluded = [b['path'] + '/' for b in repo['bundles'] if not b['eligible']]
    return [f for f in repo['files'] if not any(f['path'].startswith(p) for p in excluded)]


def summary():
    lock = manifest()
    selected = [f for r in lock['repositories'] for f in _eligible(r)]
    return {'bundle_count': lock['bundle_count'], 'eligible_bundle_count': lock['eligible_bundle_count'],
            'repository_count': len(lock['repositories']), 'file_count': len(selected),
            'total_bytes': sum(f['size'] for f in selected), 'excluded': lock['excluded']}


def active_entries(host='codex'):
    """The eight curated entry points; the remaining bundles stay library-only."""
    aliases = {'claude-code': 'claude', 'github-copilot': 'copilot'}
    host = aliases.get(host, host)
    if host not in {'codex', 'claude', 'copilot'}:
        raise fs.Conflict('Unknown team skill host')
    mapping = {
        'caveman': ('caveman', 'Caveman', 'Terse responses; preserve technical precision and scope.'),
        'ponytail': ('ponytail', 'Ponytail', 'Use the smallest complete change and verify behavior.'),
        'graphify': ('graphify', 'Graphify', 'Build or query a code knowledge graph when explicitly requested.'),
        'design-taste-frontend': ('design-taste-frontend', 'Taste', 'Design new frontend interfaces from scratch.'),
        'impeccable': ('impeccable', 'Impeccable', 'Improve, audit or polish an existing frontend interface.'),
        'karpathy-guidelines': ('karpathy-guidelines', 'Karpathy community', 'Apply community coding guidelines when explicitly requested.'),
        'obsidian-cli': ('obsidian-cli', 'Obsidian', 'Work with an Obsidian vault through its CLI.'),
        'obsidian-markdown': ('obsidian-markdown', 'Obsidian', 'Read and write Obsidian Markdown.'),
    }
    bundles = {b['name']: (r, b) for r in manifest()['repositories'] for b in r['bundles'] if b['eligible']}
    result = {}
    for name, (canonical, family, description) in mapping.items():
        repo, bundle = bundles[canonical]
        entry = bundle['entry']
        if name == 'graphify':
            entry = 'graphify/' + {'codex': 'skill-codex.md', 'claude': 'skill.md', 'copilot': 'skill-copilot.md'}[host]
        elif name == 'impeccable':
            entry = {'codex': '.agents', 'claude': '.claude', 'copilot': '.github'}[host] + '/skills/impeccable/SKILL.md'
        if entry not in {f['path'] for f in _eligible(repo)}:
            raise fs.Conflict('Missing pinned host skill entry')
        result[name] = {'path': f"{PREFIX}/{repo['slug']}/{entry}", 'family': family, 'description': description}
    return result


def _verify(item, data):
    if data is None or len(data) != item['size'] or fs.digest(data) != item['sha256']:
        raise fs.Conflict('Pinned team source hash mismatch: ' + item['path'])
    return data


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        raise fs.Conflict('Team archive download redirect refused')


def _download(repo):
    url = f"https://codeload.github.com/{repo['archive_repository']}/zip/{repo['commit']}"
    opener = urllib.request.build_opener(_NoRedirect())
    start = time.monotonic()
    try:
        with opener.open(urllib.request.Request(url, headers={'User-Agent': 'HAE-pinned-team/1'}), timeout=10) as response:
            if response.status != 200 or response.geturl() != url:
                raise fs.Conflict('Unexpected team archive response')
            chunks, size = [], 0
            while True:
                if time.monotonic() - start > DOWNLOAD_SECONDS:
                    raise fs.Conflict('Team archive download exceeded deadline')
                chunk = response.read1(min(64 * 1024, ARCHIVE_LIMIT + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > ARCHIVE_LIMIT:
                    raise fs.Conflict('Team archive exceeds download limit')
            return b''.join(chunks)
    except (OSError, urllib.error.URLError, ValueError):
        raise fs.Conflict('Unable to download pinned team archive: ' + repo['repository']) from None


def _archive_files(repo, data):
    """Validate every member, then read only allowlisted regular file bytes."""
    if len(data) > ARCHIVE_LIMIT:
        raise fs.Conflict('Team archive exceeds download limit')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > ARCHIVE_COUNT_LIMIT:
                raise fs.Conflict('Team archive exceeds member limit')
            prefix = repo['archive_repository'].split('/')[1] + '-' + repo['commit']
            selected, paths, expanded = {}, set(), 0
            wanted = {f['path']: f for f in _eligible(repo)}
            for info in members:
                _path(info.orig_filename.rstrip('/') if info.is_dir() else info.orig_filename)
                name = info.filename.rstrip('/') if info.is_dir() else info.filename
                _path(name)
                parts = PurePosixPath(name).parts
                if parts[0] != prefix:
                    raise fs.Conflict('Unexpected team archive root')
                if name.casefold() in paths:
                    raise fs.Conflict('Duplicate team archive member')
                paths.add(name.casefold())
                mode = info.external_attr >> 16
                kind = stat.S_IFMT(mode)
                if (kind not in {0, stat.S_IFREG, stat.S_IFDIR}
                        or (kind and (kind == stat.S_IFDIR) != info.is_dir())
                        or info.external_attr & 0x400):
                    raise fs.Conflict('Linked or special team archive member refused')
                if info.flag_bits & 1 or info.file_size > ARCHIVE_LIMIT or info.file_size < 0:
                    raise fs.Conflict('Unsafe team archive member')
                expanded += info.file_size
                if expanded > ARCHIVE_TOTAL_LIMIT:
                    raise fs.Conflict('Team archive exceeds expanded limit')
                relative = '/'.join(parts[1:])
                if relative in wanted and not info.is_dir():
                    item = wanted[relative]
                    if info.file_size != item['size']:
                        raise fs.Conflict('Pinned team archive size mismatch: ' + relative)
                    with archive.open(info) as stream:
                        selected[relative] = _verify(item, stream.read(FILE_LIMIT + 1))
            if set(selected) != set(wanted):
                raise fs.Conflict('Pinned team archive is missing required files')
            return selected
    except (zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError, UnicodeError, EOFError, zlib.error):
        raise fs.Conflict('Invalid team source archive') from None


def files(source_dir=None, cache_dir=None):
    """Return all eligible verified (home-relative destination, bytes) pairs.

    An offline source directory contains one <owner>--<repo> directory per
    repository. A cache contains immutable <slug>-<commit>.zip snapshots.
    No download occurs when source_dir is supplied; no code is executed.
    """
    lock = manifest()
    if source_dir is None and cache_dir is None:
        raise fs.Conflict('Team acquisition requires an explicit archive cache directory')
    source = fs.checked(source_dir) if source_dir is not None else None
    cache = fs.checked(cache_dir) if source is None else None
    staged = []
    for repo in lock['repositories']:
        wanted = _eligible(repo)
        if source is not None:
            selected = {f['path']: _verify(f, fs.read(source / repo['slug'] / f['path'], limit=FILE_LIMIT))
                        for f in wanted}
        else:
            archive_path = cache / f"{repo['slug']}-{repo['commit']}.zip"
            data = fs.read(archive_path, limit=ARCHIVE_LIMIT)
            downloaded = data is None
            if downloaded:
                data = _download(repo)
            selected = _archive_files(repo, data)
            if downloaded:
                # Cache only reviewed eligible files, never unrelated or restricted
                # source content that happened to share the downloaded archive.
                output = io.BytesIO()
                prefix = repo['archive_repository'].split('/')[1] + '-' + repo['commit'] + '/'
                with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                    for path, content in sorted(selected.items()):
                        info = zipfile.ZipInfo(prefix + path, date_time=(2026, 1, 1, 0, 0, 0))
                        info.compress_type = zipfile.ZIP_DEFLATED
                        info.external_attr = 0o100644 << 16
                        archive.writestr(info, content)
                fs.write(archive_path, output.getvalue(), expected=None)
        staged.extend((f"{PREFIX}/{repo['slug']}/{path}", content) for path, content in selected.items())
    return sorted(staged)
