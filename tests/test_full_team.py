"""Observable full-team integration and recovery in disposable profiles."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hae import fs, install, recall, team


class FullTeamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home, self.project, self.vault = [self.base / n for n in ('profile', 'project', 'memory')]
        self.project.mkdir()
        self.state = install.state_path(self.home)
        paths = {entry['path'] for host in ['claude', 'codex', 'copilot'] for entry in team.active_entries(host).values()}
        self.sources = [(path, b'# Pinned synthetic method\n') for path in sorted(paths)]
        self.executable = next(f'{team.PREFIX}/{repo["slug"]}/{item["path"]}'
                               for repo in team.manifest()['repositories'] for item in repo['files'] if item.get('executable'))
        self.sources.append((self.executable, b'#!/bin/sh\nexit 0\n'))
        self.sources.append((team.PREFIX + '/fixture/assets/image.png', b'\x89PNG\0\xff'))
        for target, value in [('runtime_bytes', b'zipapp fixture'), ('team.files', self.sources),
                              ('obsidian.status', {'app_detected': False, 'vault_registered': 'unverified'})]:
            fixture = patch('hae.install.' + target, return_value=value)
            fixture.start()
            self.addCleanup(fixture.stop)

    def plan(self, **kwargs):
        args = dict(home=self.home, state=self.state, vault=self.vault, project=self.project,
                    project_id='atlas', name='Atlas', scope='team-atlas', agents=['codex'], profile='full-team')
        return install.create_plan(**(args | kwargs))

    def test_full_team_save_recall_replan_and_uninstall(self):
        instructions = self.home / '.codex/AGENTS.md'
        instructions.parent.mkdir(parents=True)
        original = b'Keep existing team conventions.\n'
        instructions.write_bytes(original)
        plan = self.plan()
        self.assertEqual(plan['profile'], 'full-team')
        self.assertEqual(plan['conflicts'], [])
        self.assertFalse(self.vault.exists())
        self.assertTrue(any(c['diff'] is None and c['path'].endswith('.png') for c in plan['changes']))
        install.apply(self.state, plan['id'])
        self.assertIn('Caveman full and Ponytail full', instructions.read_text())
        self.assertIn('$nocaveman', instructions.read_text())
        self.assertTrue((self.vault / '.obsidian/app.json').is_file())
        self.assertTrue((self.vault / 'Home.md').is_file())
        self.assertTrue((self.home / '.agents/skills/noponytail/SKILL.md').is_file())
        policy = (self.home / '.agents/skills/graphify/agents/openai.yaml').read_text()
        self.assertIn('allow_implicit_invocation: false', policy)
        wrapper = (self.home / '.agents/skills/obsidian-markdown/SKILL.md').read_text()
        self.assertIn((self.home / team.active_entries()['obsidian-markdown']['path']).as_posix(), wrapper)
        cli_wrapper = (self.home / '.agents/skills/obsidian-cli/SKILL.md').read_text()
        self.assertIn(self.vault.as_posix(), cli_wrapper)
        self.assertIn('Never rely on the currently active vault', cli_wrapper)
        if os.name != 'nt':
            self.assertEqual((self.home / self.executable).stat().st_mode & 0o777, 0o700)
        receipt = recall.save_packet(self.vault, {'approved': True, 'mode': 'checkpoint', 'job_id': 'team-test',
            'project': 'atlas', 'scope': 'team-atlas', 'records': [{'title': 'Continuity', 'summary': 'Verified amber team continuity.'}]})
        self.assertEqual(recall.recall(self.vault, 'atlas', 'amber team continuity')['matches'][0]['path'], receipt['saved_paths'][0])
        self.assertEqual(self.plan()['changes'], [])
        install.rollback(self.state, uninstall=True)
        self.assertEqual(instructions.read_bytes(), original)
        self.assertTrue((self.vault / receipt['saved_paths'][0]).is_file())
        self.assertTrue((self.vault / '.obsidian/app.json').is_file())
        self.assertFalse((self.home / '.agents/skills/caveman/SKILL.md').exists())
        self.assertFalse((self.home / self.sources[0][0]).exists())

    def test_profile_preserves_existing_vault_preferences_and_refuses_skill_conflicts(self):
        path = self.vault / '.obsidian/app.json'
        path.parent.mkdir(parents=True)
        original = b'{"theme":"user-choice"}'
        path.write_bytes(original)
        plan = self.plan()
        install.apply(self.state, plan['id'])
        self.assertEqual(path.read_bytes(), original)
        owned = self.home / '.agents/skills/caveman/SKILL.md'
        owned.write_bytes(b'# User changed this method\n')
        with self.assertRaises(fs.Conflict):
            self.plan()
        self.assertEqual(owned.read_bytes(), b'# User changed this method\n')

    def test_core_remains_lightweight_and_full_requires_memory_engineering(self):
        with patch('hae.install.team.files') as acquire:
            plan = self.plan(profile='core')
            acquire.assert_not_called()
        self.assertFalse(any('hae-team' in c['path'] or '.obsidian' in c['path'] for c in plan['changes']))
        for kwargs in [dict(memory_enabled=False), dict(mode='general'), dict(agents=['cowork'])]:
            with self.subTest(kwargs=kwargs), self.assertRaises(fs.Conflict):
                self.plan(**kwargs)
        with self.assertRaises(fs.Conflict):
            self.plan(profile='core', team_source_dir=self.base)

    def test_full_team_installs_curated_entries_for_selected_hosts_and_plugin_delivery(self):
        plan = self.plan(agents=['claude'], delivery='plugin')
        install.apply(self.state, plan['id'])
        self.assertTrue((self.home / '.claude/skills/ponytail/SKILL.md').is_file())
        self.assertFalse((self.home / '.claude/skills/hae-setup/SKILL.md').exists())
        self.assertFalse((self.home / '.agents/skills/ponytail/SKILL.md').exists())
        self.assertFalse((self.home / '.codex/AGENTS.md').exists())
        wrapper = (self.home / '.claude/skills/graphify/SKILL.md').read_text()
        self.assertIn(team.active_entries('claude')['graphify']['path'], wrapper)

    def test_full_to_core_requires_removal_and_conflicts_do_not_acquire_sources(self):
        install.apply(self.state, self.plan()['id'])
        with patch('hae.install.team.files') as acquire:
            plan = self.plan(profile='core')
            acquire.assert_not_called()
        self.assertTrue(plan['conflicts'])
        with self.assertRaises(fs.Conflict):
            install.apply(self.state, plan['id'])
        another = self.home / '.codex/MEMORY.md'
        another.write_text('# Existing memory authority')
        with patch('hae.install.team.files') as acquire:
            plan = self.plan(project_id='second')
            acquire.assert_not_called()
        self.assertTrue(plan['conflicts'])

    def test_stale_binary_snapshot_is_rejected_before_any_destination_write(self):
        plan = self.plan()
        source = self.home / self.sources[-1][0]
        source.parent.mkdir(parents=True)
        source.write_bytes(b'user asset')
        with self.assertRaises(fs.Conflict):
            install.apply(self.state, plan['id'])
        self.assertFalse(self.vault.exists())
        self.assertEqual(source.read_bytes(), b'user asset')

    @unittest.skipIf(os.name == 'nt', 'POSIX execution permissions')
    def test_executable_permissions_restore_and_preserve_external_edits(self):
        path = self.home / self.executable
        path.parent.mkdir(parents=True)
        path.write_bytes(dict(self.sources)[self.executable])
        path.chmod(0o600)
        first = self.plan()
        install.apply(self.state, first['id'])
        self.assertEqual(path.stat().st_mode & 0o777, 0o700)
        path.chmod(0o500)
        with self.assertRaises(fs.Conflict):
            self.plan()
        with self.assertRaises(fs.Conflict):
            install.rollback(self.state, uninstall=True)
        path.chmod(0o700)
        install.rollback(self.state, uninstall=True)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.read_bytes(), dict(self.sources)[self.executable])

    @unittest.skipIf(os.name == 'nt', 'POSIX execution permissions')
    def test_inverse_requires_a_matching_content_and_mode_pair(self):
        path = self.base / 'launcher.sh'
        path.write_bytes(b'original')
        path.chmod(0o600)
        op = install.operation(path, b'upgrade', mode=0o700)
        path.chmod(0o640)
        with self.assertRaises(fs.Conflict):
            install.inverse(op)
        path.chmod(0o600)
        self.assertEqual(install.inverse(op), b'original')
        path.write_bytes(b'upgrade')
        path.chmod(0o700)
        self.assertEqual(install.inverse(op), b'original')

    @unittest.skipIf(os.name == 'nt', 'POSIX execution permissions')
    def test_removal_rechecks_preflight_permissions(self):
        install.apply(self.state, self.plan()['id'])
        target = self.home / self.executable
        save = install.save_transaction
        def change_mode(state, transaction):
            save(state, transaction)
            if transaction['status'] == 'removing':
                target.chmod(0o500)
        with patch.object(install, 'save_transaction', side_effect=change_mode):
            with self.assertRaises(fs.Conflict):
                install.rollback(self.state, uninstall=True)
        self.assertEqual(target.stat().st_mode & 0o777, 0o500)
