"""Bounded local skill discovery. No downloads, execution, or provider calls."""
import json
import itertools
from collections import deque
from pathlib import Path
from . import fs
from .packaging import resource


def routes():
    return json.loads(resource('routes.json'))


def route(home, task, explicit=False):
    rule = routes().get(task)
    if rule is None:
        raise fs.Conflict('Unknown routing task; inspect skills route --help')
    result = {'task': task, 'workflow': rule['workflow'], 'provider_calls': 0,
              'prefer_host_native': rule.get('prefer_host_native', False)}
    if rule.get('explicit_only') and not explicit:
        return result | {'status': 'explicit-request-required', 'selected': None}
    roots = [Path(home) / suffix for suffix in ['.agents/skills', '.claude/skills', '.agents/skill-library']]
    found, visited = {}, set()
    queue = deque((root, 0) for root in roots if root.is_dir())
    truncated = False
    while queue and len(visited) < 1000:
        folder, depth = queue.popleft()
        real = folder.resolve()
        if real in visited:
            continue
        visited.add(real)
        if folder.name in rule['candidates'] and (folder / 'SKILL.md').is_file():
            found.setdefault(folder.name, str((folder / 'SKILL.md').resolve()))
        if depth < 6:
            try:
                capacity = max(0, 1000 - len(visited) - len(queue))
                children = list(itertools.islice(folder.iterdir(), capacity + 1))
            except OSError:
                continue
            truncated |= len(children) > capacity
            queue.extend((p, depth + 1) for p in sorted(children[:capacity]) if p.is_dir()
                         and not p.name.startswith('.') and p.name not in {'node_modules', 'scripts', 'references'})
    selected = next(({'name': name, 'entry_file': found[name]} for name in rule['candidates'] if name in found), None)
    source = next(s for s in json.loads(resource('integrations.lock.json'))['sources'] if s['name'] == rule['family'])
    return result | {'status': 'installed' if selected else 'not-found-in-personal-folders',
        'selected': selected, 'search_truncated': truncated or bool(queue), 'searched_directories': len(visited),
        'optional_source': {'repository': source['repository'], 'commit': source['commit']},
        'fallback': 'Use the included task workflow and host-native discovery; no integration was installed.'}
