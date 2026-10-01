"""Exercise release boundaries and the runtime used by agent-led setup."""
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from hae import packaging
from tools import audit_source, build_plugins


class ReleaseTests(unittest.TestCase):
    def test_runtime_does_not_bundle_incidental_workspace_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / 'hae'
            shutil.copytree(Path(packaging.__file__).parent, root)
            (root / '.env.local').write_text('synthetic private value')
            (root / 'accidental.py').write_text('unreviewed = True')
            (root / 'resources/notes.md').write_text('synthetic personal note')
            with patch.object(packaging, '__file__', str(root / 'packaging.py')):
                data = packaging.runtime_bytes()
            with zipfile.ZipFile(io.BytesIO(data)) as zipped:
                self.assertNotIn('hae/.env.local', zipped.namelist())
                self.assertNotIn('hae/accidental.py', zipped.namelist())
                self.assertNotIn('hae/resources/notes.md', zipped.namelist())
                self.assertIn('hae/cli.py', zipped.namelist())

    def test_plugin_rebuild_excludes_stale_files_and_audit_sees_nested_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            stale = output / 'codex/hyper-agentic-engineering/notes.md'
            stale.parent.mkdir(parents=True)
            stale.write_text('synthetic old build note')
            build_plugins.build(output)
            with zipfile.ZipFile(output / 'hyper-agentic-engineering-codex.zip') as zipped:
                self.assertNotIn('notes.md', zipped.namelist())
                self.assertIn('skills/hae-setup/scripts/hae.pyz', zipped.namelist())
            inner = io.BytesIO()
            with zipfile.ZipFile(inner, 'w') as zipped:
                zipped.writestr('data.txt', 'gh' + 'p_' + 'a' * 30)
            outer = io.BytesIO()
            with zipfile.ZipFile(outer, 'w') as zipped:
                zipped.writestr('runtime.pyz', inner.getvalue())
            findings = []
            audit_source.archive(outer.getvalue(), 'fixture.zip', findings)
            self.assertEqual(findings, [{'file': 'fixture.zip!runtime.pyz!data.txt', 'reason': 'credential'}])

    def test_agent_setup_runtime_roundtrip_and_recovery_preserve_existing_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            runtime = base / 'hae.pyz'
            runtime.write_bytes(packaging.runtime_bytes())
            home, project, vault = [base / name for name in ('profile', 'project', 'memory')]
            project.mkdir()
            instructions = home / '.codex/AGENTS.md'
            instructions.parent.mkdir(parents=True)
            original = b'Keep existing review conventions.\r\n'
            instructions.write_bytes(original)

            def run(*args, data=None):
                result = subprocess.run([sys.executable, str(runtime), '--home', str(home), '--vault', str(vault), *args],
                                        input=json.dumps(data) if data else None, text=True, capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return json.loads(result.stdout)

            plan = run('plan', '--project', str(project), '--project-id', 'atlas', '--name', 'Atlas',
                       '--scope', 'personal', '--agents', 'codex')
            run('apply', plan['id'])
            run('doctor')
            self.assertEqual(run('context', '--cwd', str(project))['project_id'], 'atlas')
            packet = {'approved': True, 'job_id': 'setup-check', 'mode': 'checkpoint', 'project': 'atlas',
                      'scope': 'personal', 'records': [{'title': 'Setup verification',
                      'summary': 'Verified amber continuity checkpoint in a disposable profile.'}]}
            receipt = run('memory', 'save', '--packet', '-', data=packet)
            result = run('memory', 'recall', '--project', 'atlas', '--query', 'amber continuity')
            self.assertEqual(result['matches'][0]['path'], receipt['saved_paths'][0])
            run('uninstall')
            self.assertEqual(instructions.read_bytes(), original)
            self.assertTrue((vault / receipt['saved_paths'][0]).is_file())
