#!/usr/bin/env python3
"""Build self-contained local artifacts from reviewed source; never install them."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hae.packaging import runtime_bytes, resource, SKILL_RESOURCES


def build(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    runtime = runtime_bytes()
    (output / 'hae.pyz').write_bytes(runtime)
    source = json.loads((ROOT / 'plugins/hyper-agentic-engineering/.codex-plugin/plugin.json').read_text(encoding='utf-8'))
    for name, files in SKILL_RESOURCES.items():
        for relative, bundled in files.items():
            if (ROOT / 'skills' / name / relative).read_text(encoding='utf-8') != resource(bundled):
                raise ValueError(f'Source skill and runtime resource differ: {name}/{relative}')
    manifests = []
    for host in ['codex', 'claude', 'copilot', 'cowork']:
        plugin = output / host / 'hyper-agentic-engineering'
        plugin.mkdir(parents=True, exist_ok=True)
        # Native plugins carry skills only; setup owns hook configuration once.
        manifest_dir = '.codex-plugin' if host == 'codex' else ('.github/plugin' if host == 'copilot' else '.claude-plugin')
        manifest = dict(source)
        if host != 'codex':
            manifest.pop('interface', None)
            manifest.pop('skills', None)  # Native default skills/ discovery.
        target = plugin / manifest_dir / 'plugin.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
        (plugin / 'LICENSE').write_bytes((ROOT / 'LICENSE').read_bytes())
        shipped = [target, plugin / 'LICENSE']
        for name, files in SKILL_RESOURCES.items():
            skill = plugin / 'skills' / name
            skill.mkdir(parents=True, exist_ok=True)
            for relative, bundled in files.items():
                target = skill / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(resource(bundled), encoding='utf-8', newline='\n')
                shipped.append(target)
            text = resource(files['SKILL.md'])
            if name == 'hae-setup':
                text += f'\nThis is the {host} plugin package. Include `--delivery plugin --agents {host}` in setup plans so the installer does not duplicate plugin skills. Hooks, when selected, are configured once by the reversible installer.\n'
            (skill / 'SKILL.md').write_text(text, encoding='utf-8', newline='\n')
            (skill / 'scripts').mkdir(exist_ok=True)
            (skill / 'scripts/hae.pyz').write_bytes(runtime)
            shipped.append(skill / 'scripts/hae.pyz')
        archive = output / f'hyper-agentic-engineering-{host}.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(shipped):
                info = zipfile.ZipInfo(path.relative_to(plugin).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                zipped.writestr(info, path.read_bytes())
        manifests.append({'host': host, 'file': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})
    for name, files in SKILL_RESOURCES.items():
        skill = output / 'skills' / name
        for relative, bundled in files.items():
            target = skill / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(resource(bundled), encoding='utf-8', newline='\n')
        (skill / 'scripts').mkdir(parents=True, exist_ok=True)
        (skill / 'scripts/hae.pyz').write_bytes(runtime)
    (output / 'artifacts.json').write_text(json.dumps({'runtime_sha256': hashlib.sha256(runtime).hexdigest(), 'plugins': manifests}, indent=2) + '\n', encoding='utf-8', newline='\n')
    assets = ['hae.pyz', 'artifacts.json', *(item['file'] for item in manifests)]
    (output / 'SHA256SUMS').write_text(''.join(
        hashlib.sha256((output / name).read_bytes()).hexdigest() + '  ' + name + '\n'
        for name in sorted(assets)), encoding='utf-8', newline='\n')
    return manifests


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))
