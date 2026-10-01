import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from hae import fs, install, memory, recall, provider
from hae.cli import main, handoff


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'Profile with spaces'
        self.home.mkdir()
        self.state = install.state_path(self.home)
        self.vault = self.base / 'Existing Vault'
        self.project = self.base / 'project'
        self.project.mkdir()
        # Installer tests exercise real files/transactions without rebuilding the
        # identical distribution on every plan. The zipapp test uses the real build.
        self.runtime_fixture = patch.object(install, 'runtime_bytes', return_value=b'fixture runtime for ownership tests')
        self.runtime_fixture.start()
        self.addCleanup(self.runtime_fixture.stop)

    def plan(self, **overrides):
        args = dict(home=self.home, state=self.state, vault=self.vault, project=self.project,
                    project_id='atlas', name='Atlas', scope='personal', agents=['codex'])
        args.update(overrides)
        return install.create_plan(**args)

    def apply(self, **overrides):
        plan = self.plan(**overrides)
        self.assertFalse(plan['conflicts'])
        return install.apply(self.state, plan['id'])

    def save(self):
        return recall.save_packet(self.vault, {'approved': True, 'mode': 'remember', 'job_id': 'offline-1',
            'project': 'atlas', 'scope': 'personal', 'records': [{'title': 'Offline drafts', 'summary': 'Use SQLite for offline drafts.'}]})

    def test_plan_only_writes_private_plan(self):
        plan = self.plan()
        self.assertTrue(plan['changes'])
        self.assertFalse(self.vault.exists())
        self.assertFalse((self.home / '.codex').exists())
        if os.name != 'nt':
            self.assertEqual((self.state / 'plans' / (plan['id'] + '.json')).stat().st_mode & 0o777, 0o600)

    def test_apply_and_replan_are_idempotent(self):
        plan = self.plan(hooks=True)
        self.assertEqual(install.apply(self.state, plan['id'])['status'], 'installed')
        self.assertEqual(install.apply(self.state, plan['id'])['status'], 'unchanged')
        self.assertEqual(self.plan(hooks=True)['changes'], [])

    def test_preserves_existing_configuration_and_restores_exact_bytes(self):
        paths = {
            self.home / '.codex/config.toml': b'notify = ["keep-my-notifier"]\nmodel = "keep-my-model"\n',
            self.home / '.claude/settings.json': b'{"env":{"EXAMPLE_SETTING":"keep"},"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo existing"}]}]}}',
            self.home / '.codex/AGENTS.md': b'Keep team conventions.\n',
            self.home / '.copilot/hooks/team.json': b'{"version":1,"hooks":{}}',
        }
        for path, data in paths.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.apply(hooks=True, agents=['claude', 'codex', 'copilot'])
        self.assertEqual((self.home / '.codex/config.toml').read_bytes(), paths[self.home / '.codex/config.toml'])
        self.assertEqual(len(json.loads((self.home / '.claude/settings.json').read_bytes())['hooks']['Stop']), 2)
        install.rollback(self.state, uninstall=True)
        for path, data in paths.items():
            self.assertEqual(path.read_bytes(), data)

    def test_stale_plan_is_rejected_before_any_write(self):
        plan = self.plan()
        path = self.home / '.codex/AGENTS.md'
        path.parent.mkdir(parents=True)
        path.write_text('A concurrent author added instructions.')
        with self.assertRaises(fs.Conflict):
            install.apply(self.state, plan['id'])
        self.assertFalse(self.vault.exists())
        self.assertFalse((self.state / 'runtime').exists())

    def test_uninstall_preserves_new_notes_and_unrelated_instruction_edits(self):
        self.apply()
        receipt = self.save()
        path = self.home / '.codex/AGENTS.md'
        path.write_text(path.read_text() + '\nA later user rule.\n')
        install.rollback(self.state, uninstall=True)
        self.assertEqual(path.read_text(), '\nA later user rule.\n')
        self.assertTrue((self.vault / receipt['saved_paths'][0]).exists())
        self.assertIn('SQLite', recall.recall(self.vault, 'atlas', 'SQLite')['matches'][0]['excerpt'])

    def test_edited_owned_fragment_stops_removal_before_changes(self):
        self.apply()
        path = self.home / '.codex/AGENTS.md'
        path.write_text(path.read_text().replace('HAE continuity', 'Edited continuity'))
        config = (self.state / 'config.json').read_bytes()
        with self.assertRaises(fs.Conflict):
            install.rollback(self.state, uninstall=True)
        self.assertEqual((self.state / 'config.json').read_bytes(), config)

    def test_later_hook_additions_survive_uninstall(self):
        self.apply(hooks=True, agents=['claude'])
        path = self.home / '.claude/settings.json'
        data = json.loads(path.read_text())
        sibling = {'hooks': [{'type': 'command', 'command': 'echo later'}]}
        data['hooks']['Stop'].append(sibling)
        data['env'] = {'KEEP': 'unchanged'}
        path.write_text(json.dumps(data))
        install.rollback(self.state, uninstall=True)
        data = json.loads(path.read_text())
        self.assertEqual(data['hooks']['Stop'], [sibling])
        self.assertEqual(data['env']['KEEP'], 'unchanged')

    def test_crash_after_write_before_receipt_recovers(self):
        plan = self.plan()
        target = next(c['path'] for c in plan['changes'] if c['path'].endswith('config.json') and '/System/' not in c['path'])
        original = fs.write
        def crash(path, data, expected):
            original(path, data, expected)
            if str(path) == target:
                raise RuntimeError('simulated crash after mutation')
        with patch.object(fs, 'write', side_effect=crash):
            with self.assertRaises(RuntimeError):
                install.apply(self.state, plan['id'])
        install.rollback(self.state)
        self.assertFalse(Path(target).exists())
        self.assertEqual(install.active_transactions(self.state), [])

    def test_upgrade_rollback_and_full_uninstall(self):
        self.apply()
        original = (self.home / '.codex/AGENTS.md').read_bytes()
        second = self.apply(style='lean')
        self.assertNotEqual((self.home / '.codex/AGENTS.md').read_bytes(), original)
        install.rollback(self.state, second['id'])
        self.assertEqual((self.home / '.codex/AGENTS.md').read_bytes(), original)
        install.rollback(self.state, uninstall=True)
        self.assertFalse((self.home / '.codex/AGENTS.md').exists())

    def test_symlink_target_refused(self):
        real = self.base / 'other-person'
        real.mkdir()
        if os.name == 'nt':
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(self.home / '.claude'), str(real)], check=True, capture_output=True)
        else:
            (self.home / '.claude').symlink_to(real, target_is_directory=True)
        with self.assertRaises(fs.Conflict):
            self.plan(agents=['claude'])
        self.assertEqual(list(real.iterdir()), [])

    def test_malformed_hook_config_is_not_overwritten(self):
        path = self.home / '.codex/hooks.json'
        path.parent.mkdir(parents=True)
        path.write_text('{invalid')
        with self.assertRaises(fs.Conflict):
            self.plan(hooks=True)
        self.assertEqual(path.read_text(), '{invalid')

    def test_existing_memory_requires_a_choice(self):
        self.vault.mkdir()
        p = self.vault / 'System/memory-config.json'
        p.parent.mkdir()
        p.write_text('{"backend":"local"}')
        self.assertTrue(self.plan()['conflicts'])
        plan = self.plan(authority='hae')
        self.assertFalse(plan['conflicts'])
        install.apply(self.state, plan['id'])
        self.assertEqual(p.read_text(), '{"backend":"local"}')
        self.assertFalse(self.plan()['conflicts'])

    def test_handoff_only_does_not_create_a_memory_store(self):
        self.apply(memory_enabled=False)
        self.assertFalse(self.vault.exists())
        self.assertFalse((self.home / '.agents/skills/hae-memory').exists())
        self.assertIn('existing memory authority', (self.home / '.codex/AGENTS.md').read_text())

    def test_general_work_needs_no_git_or_engineering_practice(self):
        self.apply(mode='general')
        receipt = self.save()
        self.assertEqual(receipt['model_calls'], 0)
        result = memory.context(self.vault, str(self.project))
        self.assertEqual(result['mode'], 'general')
        self.assertTrue(result['practice'].endswith('HAE General.md'))
        recalled = recall.recall(self.vault, 'atlas', 'SQLite')
        self.assertNotIn('Engineering', str(recalled['required_context']))
        output = self.project / 'handoff.md'
        handoff(self.vault, 'atlas', {'approved': True, 'task': 'Campaign plan', 'remaining': 'Approve draft',
                                     'branch_commit': 'should not appear'}, output)
        self.assertNotIn('branch', output.read_text())

    def test_portable_zipapp_saves_and_recalls_from_another_directory(self):
        self.runtime_fixture.stop()
        self.apply()
        runtime = fs.load(self.state / 'config.json')['runtime']
        result = subprocess.run([sys.executable, runtime, '--state-dir', str(self.state), 'context', '--cwd', str(self.project)],
                                cwd=self.base, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['project_id'], 'atlas')

    def test_hook_neutral_output_and_no_transcript_read(self):
        self.runtime_fixture.stop()
        self.apply(hooks=True, agents=['copilot'])
        runtime = fs.load(self.state / 'config.json')['runtime']
        secret = self.base / 'transcript'
        secret.write_text('This must never enter the vault.')
        payload = {'cwd': str(self.project), 'sessionId': 'test', 'transcriptPath': str(secret)}
        result = subprocess.run([sys.executable, runtime, '--state-dir', str(self.state), 'hook', '--agent', 'copilot'],
                                input=json.dumps(payload), capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout), {})
        notes = list((self.vault / 'Inbox/Captures').glob('*.md'))
        self.assertEqual(len(notes), 1)
        self.assertNotIn(secret.read_text(), notes[0].read_text())
        self.assertIn('metadata-only', notes[0].read_text())

    def test_unknown_scope_captures_nothing(self):
        self.apply(hooks=True)
        memory.capture(self.vault, 'codex', {'cwd': str(self.base), 'last_assistant_message': 'Unrelated private work'})
        self.assertFalse(list((self.vault / 'Inbox/Captures').glob('*.md')))

    def test_backup_excludes_local_state_and_media(self):
        import zipfile
        self.apply()
        self.save()
        (self.vault / 'video.mp4').write_bytes(b'media')
        report = memory.backup(self.vault, self.base / 'backups')
        with zipfile.ZipFile(report['path']) as archive:
            self.assertTrue(any(n.startswith('Sessions/') for n in archive.namelist()))
            self.assertFalse(any(n.startswith(('System/', '.hae-state/')) or n.endswith('.mp4') for n in archive.namelist()))

    def test_handoff_never_overwrites_or_leaves_project(self):
        self.apply()
        packet = {'approved': True, 'task': 'Offline drafts', 'remaining': 'Verify reconnect'}
        output = self.project / 'handoff.md'
        handoff(self.vault, 'atlas', packet, output)
        with self.assertRaises(fs.Conflict):
            handoff(self.vault, 'atlas', packet, output)
        with self.assertRaises(fs.Conflict):
            handoff(self.vault, 'atlas', packet, self.base / 'outside.md')

    def test_second_project_has_separate_scope(self):
        self.apply()
        other = self.base / 'client-folder'
        other.mkdir()
        self.apply(project=other, project_id='client', name='Client', scope='client-acme')
        self.assertEqual(memory.context(self.vault, str(other))['scope'], 'client-acme')
        self.assertEqual(memory.context(self.vault, str(self.project))['scope'], 'personal')

    def test_capture_opt_in_does_not_spill_into_a_new_project(self):
        self.apply(hooks=True)
        other = self.base / 'no-capture-client'
        other.mkdir()
        self.apply(project=other, project_id='client', name='Client', scope='client-acme')
        memory.capture(self.vault, 'codex', {'cwd': str(other), 'last_assistant_message': 'Private client outcome'})
        self.assertFalse(list((self.vault / 'Inbox/Captures').glob('*.md')))

    def test_plugin_delivery_avoids_duplicate_standalone_skills(self):
        self.apply(delivery='plugin')
        self.assertFalse((self.home / '.agents/skills').exists())
        self.assertIn('HAE continuity', (self.home / '.codex/AGENTS.md').read_text())


if __name__ == '__main__':
    unittest.main()
