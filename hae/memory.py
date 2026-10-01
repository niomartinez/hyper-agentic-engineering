#!/usr/bin/env python3
"""Local Markdown memory primitives. Python 3.11+, standard library only.

Automatic captures contain only explicitly supplied final assistant text and
allowlisted metadata; transcript paths are references, never files to open.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import queue
import threading
import stat
import subprocess
import sys
import time
import uuid
import zipfile
from . import fs

MAP_NOTE = 'System/hae-projects.json'
START_NOTE = 'HAE.md'
MAX_INPUT = 131072
MAX_TEXT = 20000
MAX_FILE = 16 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_ENTRIES = 10000
REDACTED = '[REDACTED]'


class MemoryError(Exception):
    """A safe error message, containing no captured content."""


# Apply block and format rules before assignment rules so a secret is counted
# once. Incomplete private key blocks are also removed to end of supplied text.
SECRET_PATTERNS = [
    re.compile(r'-----BEGIN (?:[A-Z0-9 ]*PRIVATE KEY)-----.*?(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|\Z)', re.S),
    re.compile(r'(?i)\b(?:https?|postgres(?:ql)?|mysql|redis|mongodb(?:\+srv)?|ssh)://[^\s/@]+@'),
    re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*'),
    re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b'),
    re.compile(r'\bsk-(?:(?:proj|svcacct)-)?[A-Za-z0-9_-]{16,}\b'),
    re.compile(r'\bapikey_[A-Za-z0-9]{16,64}_[A-Za-z0-9]{32,128}\b'),
    re.compile(r'\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b'),
]
ASSIGNMENT = re.compile(
    r'''(?ix)(?P<label>(?<![\w-])["']?(?:(?:[a-z0-9]+[_-])*(?:key|token|password|passwd|secret)|apiKey|accessToken|refreshToken|clientSecret|privateKey)["']?[ \t]*[:=][ \t]*(?:\r?\n[ \t]*(?:>[ \t]*)*)?)'''
    r'''(?P<value>"[^"\r\n]*"|'[^'\r\n]*'|[^\s,;)\]}]+)'''
)


def is_placeholder(value):
    value = value.strip('"\'').strip()
    lower = value.lower()
    return (not value or lower in {'redacted', '[redacted', '[redacted]', '***', 'none', 'null', 'true', 'false', 'example', 'placeholder', 'changeme'}
            or value.startswith(('$', '<'))
            or lower.startswith(('your_', 'your-', 'example_', 'example-', 'process.env.', 'os.environ', 'getenv(', '/path/', '/users/', '~/', 'vault://')))


def redact_text(text):
    """Return (redacted text, substitution count); never print secret material."""
    count = 0
    for index, pattern in enumerate(SECRET_PATTERNS):
        def replace(match):
            nonlocal count
            if index == 1 and match.group(0).endswith('://' + REDACTED + '@'):
                return match.group(0)
            if index == 2:
                value = match.group(0).split(None, 1)[1].lower().rstrip('.')
                preceding = text[max(0, match.start() - 120):match.start()]
                explicit_header = re.search(r'''(?i)(?:proxy-)?authorization["']?\s*[:=]\s*["']?$''', preceding)
                if value in {'token', 'tokens', 'value', 'values', 'string', 'strings'} and not explicit_header:
                    return match.group(0)
            count += 1
            if index == 0:
                # Retain line and Markdown-quote structure, but no key contents.
                lines = []
                for line in match.group(0).splitlines(keepends=True):
                    prefix = re.match(r'[ \t]*(?:>[ \t]*)*', line).group(0)
                    ending = '\r\n' if line.endswith('\r\n') else ('\n' if line.endswith('\n') else '')
                    lines.append(prefix + REDACTED + ending)
                return ''.join(lines)
            if index == 1:
                return match.group(0).split('://', 1)[0] + '://' + REDACTED + '@'
            if index == 2:
                return 'Bearer ' + REDACTED
            return REDACTED
        text = pattern.sub(replace, text)

    def assignment(match):
        nonlocal count
        if is_placeholder(match.group('value')):
            return match.group(0)
        # Only complete unquoted Python lambda syntax is exempt; quoted
        # literals and bare values still require redaction.
        if (re.fullmatch(r'key[ \t]*=[ \t]*', match.group('label'))
                and re.match(r'lambda(?:[ \t]+[^:\r\n]+)?[ \t]*:', text[match.start('value'):])):
            return match.group(0)
        count += 1
        return match.group('label') + REDACTED
    return ASSIGNMENT.sub(assignment, text), count


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def vault_root(value):
    root = fs.checked(value)
    if not root.is_dir():
        raise MemoryError('vault must be an existing directory, not a symlink')
    return root.resolve()


def safe_path(root, relative, create_parent=False):
    rel = Path(relative)
    if rel.is_absolute() or rel.drive or not rel.parts or '..' in rel.parts:
        raise MemoryError('unsafe vault-relative path')
    path = root
    for part in rel.parts:
        path = path / part
        if fs.is_link(path):
            raise MemoryError('symlink paths are not permitted')
    if create_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def read_bytes(path, limit=MAX_FILE):
    path = fs.checked(path)
    fd = os.open(str(path), os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise MemoryError('only regular files are permitted')
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise MemoryError('file exceeds size limit')
    return data


def write_new(root, relative, content):
    path = safe_path(root, relative, create_parent=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
        stream.write(content)
    return path


def frontmatter(values):
    return '---\n' + ''.join('{}: {}\n'.format(key, json.dumps(value, ensure_ascii=False)) for key, value in values.items()) + '---\n\n'


def load_map(root):
    raw = json.loads(read_bytes(safe_path(root, MAP_NOTE), MAX_INPUT).decode('utf-8'))
    if not isinstance(raw, list) or len(raw) > 500:
        raise MemoryError('project map must be a bounded list')
    projects = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', str(item.get('id', ''))):
            raise MemoryError('invalid project map entry')
        if item['id'] in seen:
            raise MemoryError('duplicate project identifier')
        seen.add(item['id'])
        for field in ('name', 'scope', 'note'):
            if not isinstance(item.get(field), str) or not 0 < len(item[field]) <= 512:
                raise MemoryError('invalid project map field')
        safe_path(root, item['note'])
        paths = item.get('paths')
        if not isinstance(paths, list) or len(paths) > 100 or any(not isinstance(p, str) or not Path(p).expanduser().is_absolute() or len(p) > 2048 for p in paths):
            raise MemoryError('project paths must be absolute paths')
        projects.append(item)
    return projects


def within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def git_layout(cwd):
    """Read local repository boundaries only; never invoke hooks or remotes."""
    if cwd is None or not cwd.is_dir():
        return None
    environment = {name: value for name, value in os.environ.items() if not name.startswith('GIT_')}
    environment['GIT_OPTIONAL_LOCKS'] = '0'
    try:
        result = subprocess.run(
            ['git', '--no-optional-locks', '-c', 'core.hooksPath=' + os.devnull,
             '-C', str(cwd), 'rev-parse', '--show-toplevel', '--git-common-dir'],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, env=environment, timeout=1)
        lines = result.stdout.splitlines()
        if result.returncode or len(lines) != 2 or len(result.stdout) > 16384:
            return None
        return tuple((cwd / Path(line)).resolve() for line in lines)
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired):
        return None


def context(root, cwd, git_root=None):
    unresolved = {'status': 'unresolved', 'scope': 'unresolved', 'start_note': str(root / START_NOTE)}
    try:
        projects = load_map(root)
    except (MemoryError, OSError, ValueError, UnicodeError):
        return dict(unresolved, reason='project map unavailable or invalid')
    cwd_path = Path(cwd).expanduser().resolve() if cwd else None
    layout = git_layout(cwd_path)
    locations = [(cwd_path, layout[0] if layout else None)]
    if git_root:
        locations.append((Path(git_root).expanduser().resolve(), None))
    matches = []
    resolved_via = None
    for item in projects:
        for entry in item['paths']:
            mapped = Path(entry).expanduser().resolve()
            # A separate nested repository must have its own mapped root; a
            # containing project's directory cannot implicitly claim it.
            if any(location is not None and within(location, mapped)
                   and (top is None or within(mapped, top))
                   for location, top in locations):
                matches.append((len(mapped.parts), len(str(mapped)), item))
    if not matches and layout and layout[1].name == '.git':
        canonical_root = layout[1].parent
        for item in projects:
            for entry in item['paths']:
                mapped = Path(entry).expanduser().resolve()
                if canonical_root == mapped:
                    matches.append((len(mapped.parts), len(str(mapped)), item))
        if matches:
            resolved_via = 'git-common-dir'
    if not matches:
        return dict(unresolved, reason='no mapped project; scope remains unresolved')
    matches.sort(key=lambda match: (match[0], match[1]), reverse=True)
    best = matches[0]
    if any(m[:2] == best[:2] and m[2]['id'] != best[2]['id'] for m in matches[1:]):
        return dict(unresolved, reason='ambiguous project roots; scope remains unresolved')
    item = best[2]
    note = safe_path(root, item['note'])
    result = {'status': 'resolved', 'project_id': item['id'], 'name': item['name'], 'scope': item['scope'], 'note': str(note), 'note_exists': note.is_file(), 'start_note': str(root / START_NOTE)}
    result['mode'] = item.get('mode', 'engineering')
    result['practice'] = str(safe_path(root, item['practice'])) if item.get('practice') else None
    if resolved_via:
        result['resolved_via'] = resolved_via
    return result


def bounded_input(argument=None):
    if argument is not None:
        if len(argument.encode('utf-8')) > MAX_INPUT:
            raise MemoryError('hook input exceeds limit')
        raw = argument
    else:
        if sys.stdin.isatty():
            return {}
        # select() cannot read Windows pipes. A bounded daemon uses raw fd reads,
        # so an unclosed input pipe cannot block shutdown on a buffered I/O lock.
        result = queue.Queue(maxsize=1)
        descriptor = sys.stdin.fileno()
        if os.name == 'nt':
            import msvcrt
            msvcrt.setmode(descriptor, os.O_BINARY)
        def read_pipe():
            data = bytearray()
            try:
                while len(data) <= MAX_INPUT:
                    chunk = os.read(descriptor, min(16384, MAX_INPUT + 1 - len(data)))
                    if not chunk:
                        break
                    data.extend(chunk)
                result.put(bytes(data))
            except OSError:
                result.put(None)
        threading.Thread(target=read_pipe, daemon=True).start()
        try:
            data = result.get(timeout=0.5)
        except queue.Empty:
            raise MemoryError('hook input did not finish before deadline') from None
        if data is None or len(data) > MAX_INPUT:
            raise MemoryError('hook input unavailable or exceeds limit')
        raw = data.decode('utf-8') if data else '{}'
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise MemoryError('hook input must be an object')
    return payload


def scalar(payload, *keys):
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ''


def capture(root, agent, payload):
    from .provider import config
    if not config(root).get('capture_enabled', False):
        return
    match = context(root, scalar(payload, 'cwd'))
    if match['status'] != 'resolved':
        return
    selected = next((p for p in load_map(root) if p['id'] == match['project_id']), {})
    if selected.get('capture_enabled') is not True:
        return
    # Do not inspect nested messages, tool results, input-messages, or transcripts.
    last = scalar(payload, 'last-assistant-message', 'last_assistant_message', 'lastAssistantMessage')
    session = scalar(payload, 'thread-id', 'session_id', 'sessionId')
    turn = scalar(payload, 'turn-id', 'turn_id', 'turnId')
    cwd = scalar(payload, 'cwd')
    transcript = scalar(payload, 'transcriptPath', 'transcript_path')
    if not any((last, session, turn, cwd, transcript)):
        return
    values = {'source': agent + ' completion hook', 'agent': agent, 'actor': 'unknown', 'session_id': session, 'turn_id': turn, 'cwd': cwd, 'transcript_reference': transcript}
    redactions = 0
    for key, value in values.items():
        clean, count = redact_text(value)
        values[key] = clean[:2048]
        redactions += count
    clean, count = redact_text(last)
    redactions += count
    truncated = len(clean) > MAX_TEXT
    clean = clean[:MAX_TEXT]
    identity = json.dumps([agent, values['session_id'], values['turn_id'], values['cwd'], values['transcript_reference'], clean], ensure_ascii=False, separators=(',', ':'))
    digest = hashlib.sha256(identity.encode('utf-8')).hexdigest()
    relative = 'Inbox/Captures/capture-{}.md'.format(digest)
    if safe_path(root, relative).exists():
        return
    match = context(root, cwd) if cwd else {'scope': 'unresolved'}
    values.update({'updated': now(), 'status': 'historical/unverified', 'capture_status': 'pending', 'scope': match['scope'], 'project': match.get('project_id', 'unresolved'), 'kind': 'assistant-final' if last else 'metadata-only', 'redaction_count': redactions, 'truncated': truncated})
    body = '# Automatic session evidence\n\nThis is historical, unverified evidence. It does not establish current project status.\n\n'
    if last:
        # Quote every line so captured frontmatter/headings cannot become note metadata.
        body += '## Supplied final assistant text\n\n' + '\n'.join('> ' + line for line in clean.splitlines()) + '\n'
    else:
        body += 'No final assistant text was supplied. Transcript contents were not read.\n'
    if truncated:
        body += '\n[Text truncated to bounded capture limit.]\n'
    try:
        write_new(root, relative, frontmatter(values) + body)
    except FileExistsError:
        pass
    # Classification runs detached; capture itself never waits on an API.
    try:
        from .recall import launch
        launch(root)
    except Exception:
        pass


def record(root, args):
    projects = [p for p in load_map(root) if p['id'] == args.project]
    if not projects:
        raise MemoryError('record requires a known project identifier')
    if len(args.summary) > MAX_TEXT or len(args.next or '') > MAX_TEXT or len(args.agent) > 100 or len(args.source or '') > 2048:
        raise MemoryError('record field exceeds size limit')
    if not args.summary.strip():
        raise MemoryError('record requires a nonempty summary')
    if len(args.actor) > 200 or len(args.handoff_path or '') > 2048:
        raise MemoryError('record attribution field exceeds size limit')
    if args.handoff_path and not Path(args.handoff_path).is_absolute():
        raise MemoryError('handoff reference must be an absolute path')
    summary, n1 = redact_text(args.summary)
    actions, n2 = redact_text(args.next or 'No next action supplied.')
    source, n3 = redact_text(args.source or 'explicit curated record')
    agent, n4 = redact_text(args.agent)
    actor, n5 = redact_text(args.actor)
    handoff, n6 = redact_text(args.handoff_path or '')
    requested_title = getattr(args, 'title', None)
    if requested_title is not None and (not requested_title.strip() or len(requested_title) > 160):
        raise MemoryError('title must contain 1 to 160 characters')
    topic, n7 = redact_text(requested_title or ' '.join(summary.split()[:10]))
    def filename_part(value):
        return re.sub(r'\s+', ' ', re.sub(r'[\x00-\x1f/\\:*?"<>|#\[\]]', ' ', value)).strip(' .')[:100]
    topic = filename_part(topic) or 'Session checkpoint'
    label = filename_part(projects[0]['name']) or args.project
    operation = getattr(args, 'operation_id', None)
    if operation:
        if not re.fullmatch(r'[a-f0-9]{64}', operation):
            raise MemoryError('invalid record operation identifier')
        # Recover a successful file write if the process died before its DB receipt.
        for existing in ((root / 'Sessions').glob('*.md') if getattr(args, 'recover_record', True) else []):
            if fs.is_link(existing):
                continue
            data = read_bytes(existing)
            fields = parse_frontmatter(data)
            if fields.get('memory_operation') == operation:
                expected_body = '# ' + existing.stem + '\n\nProject context: [[' + projects[0]['note'].removesuffix('.md') + ']].\n\n## Summary\n\n' + summary + '\n\n## Next actions\n\n' + actions + '\n'
                if data.decode().split('\n---\n', 1)[-1].lstrip('\n') != expected_body or fields.get('source') != source or fields.get('project') != args.project or fields.get('scope') != projects[0]['scope']:
                    raise MemoryError('recovered record changed; inspect before retrying')
                return {'path': str(existing), 'status': 'curated', 'redaction_count': 0, 'recovered': True}
    timestamp = now()
    values = {'source': source, 'updated': timestamp, 'status': 'curated', 'project': args.project, 'scope': projects[0]['scope'], 'agent': agent, 'actor': actor, 'handoff_reference': handoff, 'redaction_count': n1 + n2 + n3 + n4 + n5 + n6 + n7}
    if operation:
        values['memory_operation'] = operation
    # Exclusive creation preserves concurrent writers; suffix only when a real collision exists.
    label = label[:60].encode('utf-8')[:80].decode('utf-8', errors='ignore')
    topic = topic.encode('utf-8')[:120].decode('utf-8', errors='ignore')
    stem = '{} — {} — {}'.format(label, topic, timestamp[:10])
    for attempt in range(1, 1001):
        title = stem + (' — {}'.format(attempt) if attempt > 1 else '')
        project_link = projects[0]['note'].removesuffix('.md')
        body = '# ' + title + '\n\nProject context: [[' + project_link + ']].\n\n## Summary\n\n' + summary + '\n\n## Next actions\n\n' + actions + '\n'
        try:
            path = write_new(root, 'Sessions/' + title + '.md', frontmatter(values) + body)
            break
        except FileExistsError:
            continue
    else:
        raise MemoryError('session filename collision limit reached')
    return {'path': str(path), 'status': 'curated', 'redaction_count': values['redaction_count']}


EXCLUDED_DIRS = {'.obsidian', '.git', '.trash', '.cache', '__pycache__', 'node_modules', '.codex', '.claude', '.copilot', '.vscode', '.hae-state', 'cache', 'caches'}
SECRET_FILENAME = re.compile(r'(?i)(?:^\.env(?:\.|$)|secret|credential|(?:^|[._-])tokens?(?:[._-]|$)|(?:^|[._-])api[_-]?keys?(?:[._-]|$)|^id_(?:rsa|dsa|ecdsa|ed25519)|\.(?:pem|key|p12|pfx|keychain)(?:$|\.)|^workspace(?:\.|$)|^ui-state(?:\.|$))')


def vault_files(root):
    """Yield safe relative file paths, with deterministic ordering and a walk cap."""
    stack = [root]
    visited = 0
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as entries:
            children = []
            for entry in entries:
                visited += 1
                if visited > MAX_ENTRIES:
                    raise MemoryError('vault exceeds entry limit')
                children.append(entry)
        for entry in sorted(children, key=lambda e: e.name):
            if fs.is_link(entry.path):
                continue
            if entry.is_dir(follow_symlinks=False):
                if entry.name.lower() not in EXCLUDED_DIRS:
                    stack.append(Path(entry.path))
            elif entry.is_file(follow_symlinks=False) and entry.name != '.DS_Store' and not SECRET_FILENAME.search(entry.name):
                yield Path(entry.path).relative_to(root)


def parse_frontmatter(data):
    text = data.decode('utf-8', errors='replace')[:8192].replace('\r\n', '\n')
    if not text.startswith('---\n'):
        return {}
    end = text.find('\n---', 4)
    if end < 0:
        return {}
    fields = {}
    for line in text[4:end].splitlines():
        match = re.match(r'^([a-z_]+):\s*(.*?)\s*$', line)
        if match:
            value = match.group(2).strip('"\'')
            fields[match.group(1)] = value
    return fields


def maintenance(root):
    projects = load_map(root)
    missing = sorted({p['note'] for p in projects if not safe_path(root, p['note']).is_file()})
    overdue = []
    unverified = []
    pending = 0
    today = dt.datetime.now(dt.timezone.utc).date()
    for relative in vault_files(root):
        if relative.suffix.lower() != '.md':
            continue
        fields = parse_frontmatter(read_bytes(safe_path(root, relative)))
        if relative.parts[0] == 'Projects' and fields.get('status') == 'historical-needs-verification':
            unverified.append(relative.as_posix())
        reviewed = fields.get('verified_at') or fields.get('last_reviewed', '')
        if reviewed == 'null':
            reviewed = ''
        if reviewed:
            try:
                if (today - dt.date.fromisoformat(reviewed[:10])).days > 14:
                    overdue.append(relative.as_posix())
            except ValueError:
                overdue.append(relative.as_posix())
        if relative.parts[:2] == ('Inbox', 'Captures') and fields.get('capture_status', 'pending') == 'pending':
            pending += 1
    result = {'updated': now(), 'overdue': sorted(overdue), 'unverified_projects': sorted(unverified), 'missing_notes': missing, 'pending_captures': pending}
    body = '# Memory health\n\nReviewed dates become overdue after 14 days. Captures require deliberate curation.\n\n'
    for heading, items in [('Unverified historical projects', result['unverified_projects']), ('Overdue reviews', result['overdue']), ('Missing mapped notes', missing)]:
        body += '## ' + heading + '\n\n' + ('\n'.join('- ' + p for p in items) if items else 'None.') + '\n\n'
    body += '## Pending captures\n\n{}\n'.format(pending)
    temporary = 'System/.health-{}.tmp'.format(uuid.uuid4())
    target = safe_path(root, 'System/Health.md')
    staging = write_new(root, temporary, frontmatter({'updated': result['updated'], 'status': 'maintenance report'}) + body)
    os.replace(str(staging), str(target))
    return result


def scan_text(data):
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return data.decode('utf-16', errors='replace')
    # Latin-1 also catches ASCII credential formats embedded in non-UTF8 files.
    try:
        return data.decode('utf-8')
    except UnicodeError:
        return data.decode('latin-1')


def backup(root, destination):
    dest = fs.checked(destination)
    if dest.is_symlink() or within(dest.resolve(), root):
        raise MemoryError('backup destination must be outside the vault and not a symlink')
    snapshots = []
    total = 0
    flagged = 0
    for relative in sorted(vault_files(root)):
        if relative.suffix.lower() != '.md' or relative.parts[0] not in {'Projects','Sessions','Practices','Profile','Handoffs'}:
            continue
        content = read_bytes(safe_path(root, relative))
        total += len(content)
        if total > MAX_TOTAL:
            raise MemoryError('vault exceeds backup size limit')
        if redact_text(scan_text(content))[1]:
            flagged += 1
        snapshots.append((relative.as_posix(), content))
    if flagged:
        raise MemoryError('backup refused: likely secrets detected in {} included file(s); no archive written'.format(flagged))
    dest.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = dest / ('hae-memory-{}-{}.zip'.format(stamp, uuid.uuid4().hex[:8]))
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for relative, content in snapshots:
                    info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100600 << 16
                    archive.writestr(info, content)
        digest = hashlib.sha256(read_bytes(path, MAX_TOTAL + 1024 * 1024)).hexdigest()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {'path': str(path), 'sha256': digest, 'files': len(snapshots), 'source_bytes': total, 'archive_bytes': path.stat().st_size}
