"""Observable full-team integration and recovery in disposable profiles."""
import json
import os
import re
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
        for skill in ['caveman', 'ponytail', 'karpathy-guidelines']:
            self.assertIn('allow_implicit_invocation: false', (self.home / '.agents/skills' / skill / 'agents/openai.yaml').read_text())
            self.assertIn('disable-model-invocation: true', (self.home / '.agents/skills' / skill / 'SKILL.md').read_text())
        for skill in ['graphify', 'context7']:
            self.assertIn('allow_implicit_invocation: true', (self.home / '.agents/skills' / skill / 'agents/openai.yaml').read_text())
            self.assertNotIn('disable-model-invocation', (self.home / '.agents/skills' / skill / 'SKILL.md').read_text())
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

    def test_graphify_is_model_invocable_on_every_host(self):
        plan = self.plan(agents=['codex', 'claude', 'copilot'])
        install.apply(self.state, plan['id'])
        for root in ['.agents/skills', '.claude/skills']:
            skill = (self.home / root / 'graphify/SKILL.md').read_text()
            self.assertNotIn('disable-model-invocation', skill)
            self.assertIn('Graphify-first applies in every git repository', skill)
            self.assertIn('graphify update <repo>', skill)
            self.assertNotIn('explicitly requests', skill)
            self.assertIn('only when the user has authorized the model cost', skill)
            self.assertIn('Skip the source skill', skill)
            self.assertIn('revert the `.gitattributes` change', skill)
            self.assertIn('allow_implicit_invocation: true', (self.home / root / 'graphify/agents/openai.yaml').read_text())
        shared = (self.home / '.agents/skills/graphify/SKILL.md').read_text()
        self.assertIn(team.active_entries('codex')['graphify']['path'], shared)
        self.assertIn(team.active_entries('copilot')['graphify']['path'], shared)
        self.assertIn(team.active_entries('claude')['graphify']['path'], (self.home / '.claude/skills/graphify/SKILL.md').read_text())

    def test_team_instructions_state_graphify_first_without_explicit_only_wording(self):
        text = install.team_instructions()
        for required in ['Graphify first', '<main checkout>/graphify-out/', 'graphify update <repo>', 'GRAPH_REPORT.md',
                         'graphify query, explain or path', 'git check-ignore -q graphify-out', 'git rev-parse --git-path info/exclude',
                         'Do not edit tracked files or global git configuration unless the user asks',
                         'Never write graphify sections, hooks or .gitattributes lines',
                         'Do not install graphify git hooks or merge drivers unless the user asks',
                         'only where hooks live in the untracked .git/hooks', 'revert the .gitattributes change',
                         'Context7', 'never npx or an unpinned latest tag',
                         'secondary store', 'configured memory authority stays authoritative', 'never run icm init, hooks or consolidate',
                         "Ignore the ICM server's own instructions", 'only when the user asks or at an approved milestone']:
            self.assertIn(required, text)
        for sentence in text.split('. '):
            if 'raphify' in sentence:
                self.assertNotIn('explicit', sentence.lower())
        # The code-only build is unconditional; the semantic layer is a separate, authorized step.
        self.assertNotIn('then the semantic layer', text)
        semantic = [sentence for sentence in text.split('. ') if 'semantic layer' in sentence]
        self.assertEqual(len(semantic), 1)
        self.assertIn('only if the user has authorized the model cost', semantic[0])
        self.assertNotIn('global git excludes', text)
        self.assertIn('Full community Karpathy guidelines require an explicit request', text)
        plan = self.plan(agents=['claude', 'codex', 'copilot'])
        install.apply(self.state, plan['id'])
        for path in ['.claude/CLAUDE.md', '.codex/AGENTS.md', '.copilot/copilot-instructions.md']:
            self.assertIn('Graphify first: in any git repository', (self.home / path).read_text())

    def test_no_hae_practice_or_skill_text_calls_graph_analysis_explicit_only(self):
        root = Path(__file__).resolve().parents[1]
        files = ['hae/resources/engineering.md', 'presets/engineering.md', 'skills/hae-engineering/references/engineering.md',
                 'skills/hae-engineering/SKILL.md', 'hae/resources/hae-engineering.md', 'README.md', 'docs/team-setup.md', 'docs/engineering.md']
        for name in files:
            text = (root / name).read_text(encoding='utf-8')
            for sentence in re.split(r'(?<=[.!?])\s+', text):
                if re.search(r'graph analysis|graphify', sentence, re.I):
                    self.assertNotRegex(sentence, r'(?i)explicit(-only|-request| opt-in)|requires? an explicit', name + ': ' + sentence)
        installed = install.team_instructions()
        self.assertNotRegex(installed, r'(?i)graph[^.]*explicit opt-in')
        plan = self.plan(agents=['claude'])
        install.apply(self.state, plan['id'])
        practice = next(self.vault.rglob('HAE Engineering.md'))
        self.assertNotIn('graph analysis are explicit', practice.read_text(encoding='utf-8'))
        self.assertIn('Graphify follows the graphify-first rule', practice.read_text(encoding='utf-8'))

    def test_context7_adapter_is_pinned_tool_neutral_and_free_of_personal_paths(self):
        entry = team.active_entries('claude')['context7']
        text = install.team_adapter('context7', entry, Path('/fixture-home'), False, {'claude': entry['path']})
        for forbidden in ['npx ctx7', '@latest', '/Users/', '/home/', 'Nio', 'niomartinez', 'Knowledge', 'npm-global', 'vault']:
            self.assertNotIn(forbidden, text)
        for required in ['ctx7 library', 'ctx7 docs', f'({team.CTX7_VERSION})', 'untrusted data', 'CTX7_TELEMETRY_DISABLED=1',
                         'Send only the library name and a generic question', 'prompt injection', 'quota',
                         '/fixture-home/' + entry['path']]:
            self.assertIn(required, text)
        self.assertNotIn('disable-model-invocation', text)
        plan = self.plan(agents=['codex'])
        install.apply(self.state, plan['id'])
        self.assertEqual((self.home / '.agents/skills/context7/SKILL.md').read_text().split('\n')[1], 'name: context7')

    def test_doctor_reports_graphify_and_ctx7_presence_without_failing_when_absent(self):
        install.apply(self.state, self.plan()['id'])
        app = {'app_detected': True, 'vault_registered': 'unverified'}
        with patch('hae.install.obsidian.status', return_value=app):
            with patch('hae.install.shutil.which', return_value=None):
                absent = install.doctor(self.state)
            with patch('hae.install.shutil.which', side_effect=lambda name: '/opt/bin/' + name if name in {'graphify', 'ctx7'} else None):
                present = install.doctor(self.state)
        self.assertEqual(absent['toolchain'], {'graphify': 'not-found', 'ctx7': 'not-found'})
        self.assertEqual(present['toolchain'], {'graphify': 'found', 'ctx7': 'found'})
        self.assertEqual((absent['status'], present['status']), ('installed', 'installed'))
        self.assertEqual((absent['issues'], present['issues']), ([], []))
        self.assertNotIn('/opt/bin', json.dumps(present))

    def test_setup_guide_pins_the_toolchain_and_keeps_icm_secondary(self):
        text = (Path(__file__).resolve().parents[1] / 'SETUP.md').read_text(encoding='utf-8')
        for required in [f'graphifyy=={team.GRAPHIFY_VERSION}', f'ctx7@{team.CTX7_VERSION}', 'GRAPHIFY_NO_AUTO_REFRESH=1',
                         'CTX7_TELEMETRY_DISABLED=1', 'graphify-out/', 'graphify update <repo>', '`.gitattributes`', 'checksums.txt',
                         'Never run `icm init`', 'icm --no-embeddings serve --compact', 'store_raw = false', 'one memory authority',
                         'HAE does not write MCP configuration', 'Undo.', 'untested on Windows', 'git check-ignore -q graphify-out',
                         '9722846e627a369150107dd792145c3e3a53e3d3da46f7a7bff9f96b75da857c',
                         '3d7ea3ca073d2c815d932453e7b412dbe4d7a7be109ce6ae0b3ff00e1231f541',
                         'sha512-iEhY9CS2aujMLbSh6WqFPiZgUTUuU+RRvANoNlX+PYUuwlpup83joVjVoI3Xvok6nlHeESYiqH4AhoDmiYiukA==',
                         'in each host\'s environment', 'rtk-ai/icm', 'Apache-2.0', 'only when the user asks', 'merge.graphify.driver']:
            self.assertIn(required, text)
        security = (Path(__file__).resolve().parents[1] / 'SECURITY.md').read_text(encoding='utf-8')
        self.assertIn('transitive dependencies are not pinned', security)
        self.assertNotIn('install -g ctx7@latest', text)

    def test_core_doctor_has_no_toolchain_section(self):
        install.apply(self.state, self.plan(profile='core')['id'])
        with patch('hae.install.shutil.which', return_value=None):
            self.assertNotIn('toolchain', install.doctor(self.state))

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
