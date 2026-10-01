"""Bounded files, compare-before-write replacement, and local process locking."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile


class Conflict(Exception):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def checked(path):
    path = Path(os.path.abspath(Path(path).expanduser()))
    for parent in [*reversed(path.parents), path]:
        if is_link(parent):
            raise Conflict(f'Linked or reparse-point destination refused: {parent}')
    return path


def is_link(path):
    """Include Windows junctions/reparse points on Python 3.11 as well."""
    try:
        info = Path(path).lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def read(path, limit=8 * 1024 * 1024):
    path = checked(path)
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    except FileNotFoundError:
        return None
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Conflict(f'Not a regular file: {path}')
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise Conflict(f'File exceeds limit: {path}')
    return data


def write(path, data, expected):
    path = checked(path)
    if digest(read(path)) != expected:
        raise Conflict(f'File changed since review: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    checked(path)
    fd, temporary = tempfile.mkstemp(prefix='.hae-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if digest(read(path)) != expected:
            raise Conflict(f'File changed during write: {path}')
        mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()


def load(path, default=None):
    data = read(path)
    if data is None:
        return default
    try:
        return json.loads(data)
    except (ValueError, UnicodeError):
        raise Conflict(f'Invalid JSON: {path}') from None


def save(path, value):
    write(path, json_bytes(value), digest(read(path)))


@contextlib.contextmanager
def file_lock(path):
    """Nonblocking process lock, released on exit or process termination."""
    path = checked(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('a+b') as stream:
        os.chmod(path, 0o600)
        if os.name == 'nt':
            import msvcrt
            acquire = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            release = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            acquire = lambda: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            release = lambda: fcntl.flock(stream, fcntl.LOCK_UN)
        stream.seek(0)
        try:
            acquire()
        except OSError:
            raise Conflict('Another operation holds this lock, or the filesystem cannot lock it') from None
        try:
            yield
        finally:
            stream.seek(0)
            release()


def lock(state):
    return file_lock(checked(state) / 'installer.lock')
