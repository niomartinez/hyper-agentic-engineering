"""Real filesystem, subprocess and shell checks, also run on native Windows CI."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from hae import commands, fs, install, memory, recall, skills
from hae.packaging import resource, SKILL_RESOURCES


class PortableTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / "Jo's $space & équipe"
        self.home.mkdir()
        self.state = install.state_path(self.home)
        self.project = self.base / 'project'
        self.project.mkdir()
        self.vault = self.base / 'Vault'

    def plan(self, **kw):
        return install.create_plan(home=self.home, state=self.state, vault=self.vault,
            project=self.project, project_id='atlas', name='Équipe 東京', scope='personal', **kw)

    def test_binary_reads_and_atomic_writes_preserve_all_bytes(self):
        path = self.base / 'binary'
        data = bytes(range(256)) + b'\r\n\x1a\r\n'
        fs.write(path, data, None)
        self.assertEqual(fs.read(path), data)
        fs.write(path, data[::-1], fs.digest(data))
        self.assertEqual(fs.read(path), data[::-1])

    def test_process_lock_exclusion_and_release(self):
        path = self.base / 'test.lock'
        script = "from hae import fs; import sys\ntry:\n with fs.file_lock(sys.argv[1]): pass\nexcept fs.Conflict: sys.exit(12)"
        with fs.file_lock(path):
            result = subprocess.run([sys.executable, '-c', script, str(path)], capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 12, result.stderr)
        result = subprocess.run([sys.executable, '-c', script, str(path)], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unclosed_hook_input_has_a_deadline(self):
        process = subprocess.Popen([sys.executable, '-c',
            'from hae.memory import bounded_input, MemoryError\ntry: bounded_input()\nexcept MemoryError: print("bounded")'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            process.wait(timeout=5)
            self.assertEqual(process.stdout.read().strip(), b'bounded')
            self.assertEqual(process.returncode, 0)
        finally:
            if process.poll() is None:
                process.kill(); process.wait()
            process.stdin.close(); process.stdout.close(); process.stderr.close()

    def test_real_generated_hooks_and_unicode_memory_roundtrip(self):
        plan = self.plan(hooks=True, agents=['claude', 'codex', 'copilot'])
        install.apply(self.state, plan['id'])
        configs = {
            'claude': fs.load(self.home / '.claude/settings.json')['hooks']['Stop'][0]['hooks'][0],
            'codex': fs.load(self.home / '.codex/hooks.json')['hooks']['Stop'][0]['hooks'][0],
            'copilot': fs.load(self.home / '.copilot/hooks/hae.json')['hooks']['agentStop'][0],
        }
        payload = json.dumps({'cwd': str(self.project), 'session_id': 'cross-platform',
                              'last_assistant_message': 'Verified local Unicode storage: 東京.'})
        for agent, config in configs.items():
            with self.subTest(agent=agent):
                if agent == 'codex':
                    argv = ['cmd', '/d', '/s', '/c', config['commandWindows']] if os.name == 'nt' else ['sh', '-c', config['command']]
                else:
                    argv = [config.get('exec', config.get('command')), *config['args']]
                result = subprocess.run(argv, input=payload, text=True, capture_output=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {})
        self.assertEqual(len(list((self.vault / 'Inbox/Captures').glob('*.md'))), 3)
        data = {'approved': True, 'mode': 'remember', 'job_id': 'unicode-1', 'project': 'atlas',
                'scope': 'personal', 'records': [{'title': 'Décision 東京', 'summary': 'Use SQLite for 東京 drafts.'}]}
        receipt = recall.save_packet(self.vault, data)
        relative = receipt['saved_paths'][0]
        self.assertNotIn('\\', relative)
        self.assertIn('東京', (self.vault / relative).read_text(encoding='utf-8'))
        self.assertNotIn(b'\r\n', (self.vault / relative).read_bytes())
        self.assertEqual(recall.recall(self.vault, 'atlas', 'SQLite')['matches'][0]['path'], relative)
        original = recall.read_note(self.vault, 'Projects/atlas.md')
        recall.save_packet(self.vault, {'approved': True, 'mode': 'override', 'job_id': 'unicode-2',
            'project': 'atlas', 'scope': 'personal', 'updates': [{'path': 'Projects/atlas.md',
            'content': original + '\nDécision 東京 retained.\n', 'expected_sha256': recall.sha(original)}]})
        self.assertIn('東京 retained', recall.read_note(self.vault, 'Projects/atlas.md'))
        install.rollback(self.state, uninstall=True)
        self.assertTrue((self.vault / relative).exists())

    def test_generated_preview_apply_runs_in_native_shell(self):
        with patch.object(install, 'runtime_bytes', return_value=b'installer fixture'):
            plan = self.plan(agents=['codex'])
        if os.name == 'nt':
            argv = ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', plan['apply']]
        else:
            argv = ['sh', '-c', plan['apply']]
        result = subprocess.run(argv, cwd=self.base, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'installed')

    def test_crlf_metadata_is_recognized(self):
        text = memory.frontmatter({'project': 'atlas', 'scope': 'personal'}).replace('\n', '\r\n')
        self.assertEqual(memory.parse_frontmatter(text.encode())['project'], 'atlas')
        self.assertEqual(recall.metadata(text)['scope'], 'personal')

    def test_crlf_recall_does_not_rank_metadata_as_memory(self):
        with patch.object(install, 'runtime_bytes', return_value=b'installer fixture'):
            plan = self.plan(agents=['codex'])
            install.apply(self.state, plan['id'])
        header = memory.frontmatter({'project': 'atlas', 'scope': 'personal'})
        memory.write_new(self.vault, 'Sessions/noise.md', (header + '# Layout\nSpacing adjusted.\n').replace('\n', '\r\n'))
        memory.write_new(self.vault, 'Sessions/storage.md', (header + '# Storage\nUse SQLite for drafts.\n').replace('\n', '\r\n'))
        result = recall.recall(self.vault, 'atlas', 'atlas SQLite')
        self.assertEqual(result['matches'][0]['path'], 'Sessions/storage.md')
        self.assertNotIn('Sessions/noise.md', [item['path'] for item in result['matches']])

    def test_reserved_windows_identifiers_are_refused_on_every_platform(self):
        for name in ['CON', 'nul.md', 'COM1', 'LPT9', 'atlas.']:
            with self.subTest(name=name), self.assertRaises(fs.Conflict):
                install.identity(name)

    def test_general_setup_does_not_install_engineering_workflows(self):
        with patch.object(install, 'runtime_bytes', return_value=b'installer fixture'):
            plan = self.plan(mode='general', agents=['codex'])
            install.apply(self.state, plan['id'])
        self.assertFalse((self.home / '.agents/skills/hae-engineering').exists())

    def test_engineering_practice_upgrade_preserves_user_edits(self):
        with patch.object(install, 'runtime_bytes', return_value=b'installer fixture'):
            first = self.plan(agents=['codex'])
            install.apply(self.state, first['id'])
            path = self.vault / 'Practices/HAE Engineering.md'
            path.write_bytes(path.read_bytes() + b'\nTeam rule: use the approved CI runner.\n')
            before = path.read_bytes()
            second = self.plan(agents=['codex'])
            install.apply(self.state, second['id'])
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue(any('practice edits' in str(w) for w in second['warnings']))
        self.assertIn('assumptions', (self.home / '.agents/skills/hae-engineering/references/engineering.md').read_text(encoding='utf-8'))

    def test_untouched_old_practice_is_upgraded(self):
        def old_resource(name):
            return '# Original small practice\n' if name == 'engineering.md' else resource(name)
        with patch.object(install, 'runtime_bytes', return_value=b'installer fixture'):
            with patch.object(install, 'resource', side_effect=old_resource):
                first = self.plan(agents=['codex'])
                install.apply(self.state, first['id'])
            second = self.plan(agents=['codex'])
            install.apply(self.state, second['id'])
        self.assertIn('assumptions', (self.vault / 'Practices/HAE Engineering.md').read_text(encoding='utf-8'))

    def test_crlf_conversion_preserves_unrelated_bytes_through_upgrade_and_removal(self):
        with patch.object(install, 'runtime_bytes', return_value=b'installer fixture'):
            first = self.plan(agents=['codex'])
            install.apply(self.state, first['id'])
            path = self.home / '.codex/AGENTS.md'
            suffix = b'\r\nTeam rule with Windows line endings.\r\n'
            path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n') + suffix)
            second = self.plan(agents=['codex'], style='lean')
            install.apply(self.state, second['id'])
            self.assertTrue(path.read_bytes().endswith(suffix))
            install.rollback(self.state, uninstall=True)
        self.assertEqual(path.read_bytes(), suffix)

    def test_routes_choose_one_installed_method_and_respect_opt_in(self):
        for name in ['design-taste-frontend', 'impeccable', 'karpathy-guidelines', 'diagnosing-bugs']:
            folder = self.home / '.agents/skills' / name
            folder.mkdir(parents=True); (folder / 'SKILL.md').write_text('# Synthetic skill', encoding='utf-8')
        self.assertEqual(skills.route(self.home, 'ui-new')['selected']['name'], 'design-taste-frontend')
        self.assertEqual(skills.route(self.home, 'ui-existing')['selected']['name'], 'impeccable')
        self.assertEqual(skills.route(self.home, 'bug')['selected']['name'], 'diagnosing-bugs')
        self.assertIsNone(skills.route(self.home, 'karpathy')['selected'])
        self.assertEqual(skills.route(self.home, 'karpathy', explicit=True)['selected']['name'], 'karpathy-guidelines')
        self.assertEqual(skills.route(self.home, 'tests')['status'], 'not-found-in-personal-folders')

    def test_router_finds_categorized_library_without_loading_all_skills(self):
        folder = self.home / '.agents/skill-library/snapshot/matt-skills/skills/engineering/diagnosing-bugs'
        folder.mkdir(parents=True); (folder / 'SKILL.md').write_text('# Synthetic skill', encoding='utf-8')
        result = skills.route(self.home, 'bug')
        self.assertEqual(result['selected']['entry_file'], str(folder / 'SKILL.md'))
        self.assertFalse(result['search_truncated'])

    def test_packaged_skill_references_match_source(self):
        root = Path(__file__).resolve().parents[1]
        for name, files in SKILL_RESOURCES.items():
            for relative, source in files.items():
                self.assertEqual((root / 'skills' / name / relative).read_text(encoding='utf-8'), resource(source))
