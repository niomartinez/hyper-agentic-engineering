"""Build a reproducible, dependency-free Python zipapp from this package."""
import importlib.resources
import io
from pathlib import Path
import sys
import zipfile

from . import fs

# Explicit shipping boundary: an untracked file must never become a release asset.
RUNTIME_MODULES = ('__init__.py', '__main__.py', 'cli.py', 'commands.py', 'fs.py',
                   'install.py', 'memory.py', 'packaging.py', 'provider.py', 'recall.py', 'skills.py')
RESOURCE_FILES = ('LICENSE', 'engineering.md', 'general.md', 'hae-engineering.md',
                  'hae-memory.md', 'hae-setup.md', 'integrations.lock.json', 'packets.md',
                  'routes.json', 'vault.md', 'workflows.md')

SKILL_RESOURCES = {
    'hae-setup': {'SKILL.md': 'hae-setup.md', 'references/packets.md': 'packets.md'},
    'hae-memory': {'SKILL.md': 'hae-memory.md', 'references/packets.md': 'packets.md'},
    'hae-engineering': {'SKILL.md': 'hae-engineering.md', 'references/engineering.md': 'engineering.md',
                        'references/workflows.md': 'workflows.md'},
}


def resources():
    return importlib.resources.files('hae').joinpath('resources')


def resource(name):
    return resources().joinpath(name).read_text(encoding='utf-8')


def runtime_bytes():
    if zipfile.is_zipfile(sys.argv[0]):
        return Path(sys.argv[0]).read_bytes()
    output = io.BytesIO()
    def add(archive, name, data):
        info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, data)
    root = Path(__file__).parent
    with zipfile.ZipFile(output, 'w') as archive:
        add(archive, '__main__.py', b'from hae.cli import main\nraise SystemExit(main())\n')
        for relative in sorted([*RUNTIME_MODULES, *('resources/' + name for name in RESOURCE_FILES)]):
            data = fs.read(root / relative)
            if data is None:
                raise fs.Conflict('Missing required runtime file: ' + relative)
            add(archive, 'hae/' + relative, data)
    return output.getvalue()


def runtime_command():
    if zipfile.is_zipfile(sys.argv[0]):
        return [sys.executable, str(Path(sys.argv[0]).absolute())]
    return [sys.executable, str(Path(__file__).parent.parent / 'run.py')]
