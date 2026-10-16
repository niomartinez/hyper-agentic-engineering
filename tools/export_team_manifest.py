#!/usr/bin/env python3
"""Export hashes and portable paths from a reviewed installed skill inventory.

This maintenance tool reads source files without copying their contents into HAE.
The output contains no source-machine paths, descriptions, or account metadata.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hae import fs

# Preserve dependencies as inert files; never install their plugins or hooks.
SIDECARS = {
    'JuliusBrussee/caveman': ['agents/cavecrew-investigator.md', 'agents/cavecrew-builder.md',
                               'agents/cavecrew-reviewer.md', 'src/hooks/caveman-stats.js',
                               'src/hooks/caveman-config.js', 'src/hooks/caveman-parse.js',
                               'LICENSING.md', 'TRADEMARKS.md'],
    'Graphify-Labs/graphify': ['pyproject.toml'],
    'pbakaus/impeccable': ['.claude/skills/impeccable', '.github/skills/impeccable'],
    # Skills link to the shared checklists as ../../references/*.md. Commands,
    # personas, hooks, scripts and evals stay out of the pin.
    'addyosmani/agent-skills': ['references'],
}
RESTRICTED = {'docx', 'pdf', 'pptx', 'xlsx'}
# In the private inventory but deliberately not pinned. HAE documents the MCP
# option instead of shipping its tool-call skill.
OMIT = {('upstash/context7', 'context7-mcp')}


def export(inventory, source_dir=None):
    data = json.loads(fs.read(inventory))
    library = Path(source_dir or data['library'])
    result = {'schema_version': 1, 'bundle_count': 0,
              'install_prefix': '.agents/skill-library/hae-team', 'repositories': [],
              'excluded': [{'repository': 'anthropics/skills', 'name': name,
                            'reason': 'Pinned upstream license prohibits retaining copies outside Services; use host-native tools.'}
                           for name in sorted(RESTRICTED) if any(s['repo'] == 'anthropics/skills'
                                                                 and s['name'] == name for s in data['skills'])]}
    for repo in data['repositories']:
        slug = repo['repo'].replace('/', '--')
        # A pinned snapshot can live in a versioned folder, for example <slug>-1.2.3.
        original_root = Path(repo.get('directory') or Path(data['library']) / slug)
        root = fs.checked(library / original_root.relative_to(data['library']))
        selected = set()
        bundles = []
        for skill in data['skills']:
            if skill['repo'] != repo['repo'] or (repo['repo'], skill['name']) in OMIT:
                continue
            # The private prefix is used only to recover the reviewed repo path.
            path = Path(skill['path']).relative_to(original_root)
            entry = Path(skill['entry_file']).relative_to(original_root)
            if fs.digest(fs.read(root / entry)) != skill['sha256']:
                raise fs.Conflict(f'Installed entry differs from inventory: {slug}/{entry}')
            selected.update(p for p in (root / path).rglob('*') if p.is_file())
            bundles.append({'name': skill['name'], 'path': path.as_posix(),
                            'entry': entry.as_posix(), 'sha256': skill['sha256'],
                            'eligible': not (repo['repo'] == 'anthropics/skills' and skill['name'] in RESTRICTED),
                            'license': 'Anthropic-service-terms' if repo['repo'] == 'anthropics/skills'
                            and skill['name'] in RESTRICTED else 'upstream-notices'})
        for p in root.iterdir():
            if p.is_file() and (p.name in {'README.md', 'package.json'}
                               or p.name.upper().startswith(('LICENSE', 'NOTICE', 'COPYING'))):
                selected.add(p)
        for extra in SIDECARS.get(repo['repo'], []):
            p = root / extra
            if p.is_dir():
                selected.update(x for x in p.rglob('*') if x.is_file())
            elif p.is_file():
                selected.add(p)
        files = []
        for path in sorted(selected):
            content = fs.read(path, limit=16 * 1024 * 1024)
            files.append({'path': path.relative_to(root).as_posix(),
                          'sha256': hashlib.sha256(content).hexdigest(), 'size': len(content),
                          'executable': bool(path.stat().st_mode & 0o111)})
        canonical_repo = repo['url'].removeprefix('https://github.com/').rstrip('/')
        result['repositories'].append({'repository': repo['repo'], 'archive_repository': canonical_repo,
                                       'slug': slug, 'commit': repo['commit'],
                                       'bundles': sorted(bundles, key=lambda b: b['path']), 'files': files})
    result['bundle_count'] = sum(len(r['bundles']) for r in result['repositories'])
    result['eligible_bundle_count'] = sum(b['eligible'] for r in result['repositories'] for b in r['bundles'])
    result['file_count'] = sum(len(r['files']) for r in result['repositories'])
    result['total_bytes'] = sum(f['size'] for r in result['repositories'] for f in r['files'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', required=True, type=Path)
    parser.add_argument('--source-dir', type=Path)
    parser.add_argument('--output', type=Path, default=Path('hae/resources/team-skills.lock.json'))
    args = parser.parse_args()
    result = export(args.inventory, args.source_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(fs.json_bytes(result))
    print(json.dumps({k: result[k] for k in ['bundle_count', 'file_count', 'total_bytes']}))


if __name__ == '__main__':
    main()
