import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
from unittest.mock import patch
import zipfile

from hae import fs, team


COMMIT = 'a' * 40
CONTENT = b'---\nname: demo\n---\nUse the example.\n'
BINARY = b'\x00\xff\xfe\x80asset'
RESTRICTED = b'License-restricted example'


def fixture_lock():
    items = [('skills/demo/SKILL.md', CONTENT), ('skills/demo/assets/example.bin', BINARY),
             ('skills/restricted/SKILL.md', RESTRICTED)]
    return {'schema_version': 1, 'bundle_count': 2, 'eligible_bundle_count': 1,
            'install_prefix': team.PREFIX, 'excluded': [{'name': 'restricted', 'reason': 'fixture'}],
            'repositories': [{'repository': 'example/skills', 'archive_repository': 'example/skills',
                              'slug': 'example--skills', 'commit': COMMIT,
                              'bundles': [{'name': 'demo', 'path': 'skills/demo',
                                           'entry': items[0][0], 'eligible': True},
                                          {'name': 'restricted', 'path': 'skills/restricted',
                                           'entry': items[2][0], 'eligible': False}],
                              'files': [{'path': path, 'size': len(data), 'sha256': fs.digest(data)}
                                        for path, data in items]}]}


def archive_bytes(extra=None, content=CONTENT, include_asset=True):
    output = io.BytesIO()
    prefix = 'skills-' + COMMIT + '/'
    with warnings.catch_warnings(), zipfile.ZipFile(output, 'w') as archive:
        warnings.simplefilter('ignore', UserWarning)
        archive.writestr(prefix + 'skills/demo/SKILL.md', content)
        if include_asset:
            archive.writestr(prefix + 'skills/demo/assets/example.bin', BINARY)
        archive.writestr(prefix + 'skills/restricted/SKILL.md', RESTRICTED)
        if extra:
            name, data, mode = extra
            info = zipfile.ZipInfo(name)
            # ZipInfo normalizes Windows separators at construction. Preserve
            # the malicious archive spelling so the fixture tests the reader.
            info.filename = name
            info.external_attr = mode << 16
            archive.writestr(info, data)
    return output.getvalue()


class TeamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.lock = fixture_lock()
        self.resource = patch.object(team, 'resource', return_value=json.dumps(self.lock))
        self.resource.start()
        self.addCleanup(self.resource.stop)

    def source(self):
        source = self.root / 'source'
        for repo in self.lock['repositories']:
            for item in repo['files']:
                path = source / repo['slug'] / item['path']
                path.parent.mkdir(parents=True, exist_ok=True)
                data = {fs.digest(x): x for x in [CONTENT, BINARY, RESTRICTED]}[item['sha256']]
                path.write_bytes(data)
        return source

    def test_offline_snapshot_binary_preserved_exclusions_not_read(self):
        source = self.source()
        restricted = source / 'example--skills/skills/restricted/SKILL.md'
        restricted.unlink()
        with patch.object(team, '_download', side_effect=AssertionError('no network')):
            selected = dict(team.files(source_dir=source))
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[team.PREFIX + '/example--skills/skills/demo/assets/example.bin'], BINARY)
        self.assertFalse(any('restricted' in p for p in selected))

    def test_source_hash_mismatch_and_missing_file_refused(self):
        source = self.source()
        entry = source / 'example--skills/skills/demo/SKILL.md'
        entry.write_bytes(CONTENT.replace(b'example', b'changed'))
        with self.assertRaisesRegex(fs.Conflict, 'hash mismatch'):
            team.files(source_dir=source)
        entry.unlink()
        with self.assertRaisesRegex(fs.Conflict, 'hash mismatch'):
            team.files(source_dir=source)

    def test_symlink_source_parent_refused(self):
        source = self.source()
        link = self.root / 'linked'
        try:
            link.symlink_to(source, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('host cannot create symlinks')
        with self.assertRaisesRegex(fs.Conflict, 'Linked'):
            team.files(source_dir=link)

    def test_cache_uses_verified_archive_without_network(self):
        cache = self.root / 'cache'
        cache.mkdir()
        (cache / ('example--skills-' + COMMIT + '.zip')).write_bytes(archive_bytes())
        with patch.object(team, '_download', side_effect=AssertionError('no network')):
            self.assertEqual(len(team.files(cache_dir=cache)), 2)

    def test_download_staged_and_cached_only_after_validation(self):
        cache = self.root / 'cache'
        with patch.object(team, '_download', return_value=archive_bytes()):
            self.assertEqual(len(team.files(cache_dir=cache)), 2)
        cached = cache / ('example--skills-' + COMMIT + '.zip')
        self.assertTrue(cached.is_file())
        with zipfile.ZipFile(cached) as archive:
            self.assertFalse(any('restricted' in name for name in archive.namelist()))
        with patch.object(team, '_download', side_effect=AssertionError('no network')):
            self.assertEqual(len(team.files(cache_dir=cache)), 2)
        bad_cache = self.root / 'bad-cache'
        with patch.object(team, '_download', return_value=b'invalid'):
            with self.assertRaises(fs.Conflict):
                team.files(cache_dir=bad_cache)
        self.assertFalse(bad_cache.exists())

    def test_archive_hash_missing_and_corruption_refused(self):
        repo = self.lock['repositories'][0]
        for data in [archive_bytes(content=CONTENT.replace(b'example', b'changed')),
                     archive_bytes(include_asset=False), b'broken archive']:
            with self.subTest(data=data[:12]):
                with self.assertRaises(fs.Conflict):
                    team._archive_files(repo, data)

    def test_archive_traversal_absolute_symlink_duplicates_refused(self):
        prefix = 'skills-' + COMMIT + '/'
        cases = [('outside/../../attack', b'x', stat.S_IFREG),
                 ('/absolute', b'x', stat.S_IFREG),
                 (prefix + 'skills/demo/SKILL.md', CONTENT, stat.S_IFREG),
                 (prefix + 'unrelated/COn.txt', b'x', stat.S_IFREG),
                 (prefix + 'unrelated/x\\y', b'x', stat.S_IFREG)]
        for extra in cases:
            with self.subTest(name=extra[0]):
                with self.assertRaises(fs.Conflict):
                    team._archive_files(self.lock['repositories'][0], archive_bytes(extra=extra))

    def test_unselected_link_is_ignored_but_selected_link_and_special_members_are_refused(self):
        repo = self.lock['repositories'][0]
        prefix = 'skills-' + COMMIT + '/'
        # Upstream repositories can carry a link outside the pinned paths. It is never read or followed.
        linked = archive_bytes(extra=(prefix + '.tool/skills', b'../skills/', stat.S_IFLNK))
        self.assertEqual(set(team._archive_files(repo, linked)), {'skills/demo/SKILL.md', 'skills/demo/assets/example.bin'})
        for name, kind in [(prefix + 'unrelated/pipe', stat.S_IFIFO), (prefix + 'unrelated/dir-link/', stat.S_IFLNK)]:
            with self.subTest(name=name), self.assertRaisesRegex(fs.Conflict, 'Special'):
                team._archive_files(repo, archive_bytes(extra=(name, b'', kind)))
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            for path, data, kind in [('skills/demo/SKILL.md', b'../outside', stat.S_IFLNK),
                                     ('skills/demo/assets/example.bin', BINARY, stat.S_IFREG)]:
                info = zipfile.ZipInfo(prefix + path)
                info.external_attr = kind << 16
                archive.writestr(info, data)
        with self.assertRaisesRegex(fs.Conflict, 'Linked'):
            team._archive_files(repo, output.getvalue())

    def test_archive_rejects_raw_backslash_after_windows_normalization(self):
        name = 'skills-' + COMMIT + '/unrelated/x\\y'
        data = archive_bytes(extra=(name, b'x', stat.S_IFREG))
        with patch.object(zipfile.os, 'sep', '\\'):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                member = archive.infolist()[-1]
                self.assertEqual(member.orig_filename, name)
                self.assertEqual(member.filename, name.replace('\\', '/'))
            with self.assertRaisesRegex(fs.Conflict, 'Unsafe team source path'):
                team._archive_files(self.lock['repositories'][0], data)
            # Ordinary pinned paths remain valid under the same normalization.
            self.assertEqual(len(team._archive_files(self.lock['repositories'][0], archive_bytes())), 2)

    def test_archive_byte_count_and_expansion_limits(self):
        repo = self.lock['repositories'][0]
        for name, limit in [('ARCHIVE_LIMIT', 10), ('ARCHIVE_COUNT_LIMIT', 1), ('ARCHIVE_TOTAL_LIMIT', 1)]:
            with self.subTest(limit=name), patch.object(team, name, limit):
                with self.assertRaises(fs.Conflict):
                    team._archive_files(repo, archive_bytes())

    def test_manifest_path_and_commit_tampering_refused(self):
        for field, value in [('slug', '../outside'), ('commit', 'main'), ('archive_repository', '../x')]:
            changed = fixture_lock()
            changed['repositories'][0][field] = value
            with self.subTest(field=field), patch.object(team, 'resource', return_value=json.dumps(changed)):
                with self.assertRaises(fs.Conflict):
                    team.manifest()
        for path in ['../outside', 'a/../outside', '/absolute', 'a\\b', 'NUL.txt', 'x:stream', 'a//b', 'a/./b']:
            changed = fixture_lock()
            changed['repositories'][0]['files'][0]['path'] = path
            with self.subTest(path=path), patch.object(team, 'resource', return_value=json.dumps(changed)):
                with self.assertRaises(fs.Conflict):
                    team.manifest()

    def test_download_limits_and_deadline_without_live_network(self):
        class Response:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass
            def geturl(self):
                return 'https://codeload.github.com/example/skills/zip/' + COMMIT
            def read1(self, size):
                return b'x' * size
        opener = unittest.mock.Mock()
        opener.open.return_value = Response()
        with patch.object(team.urllib.request, 'build_opener', return_value=opener):
            with patch.object(team, 'ARCHIVE_LIMIT', 10):
                with self.assertRaisesRegex(fs.Conflict, 'download limit'):
                    team._download(self.lock['repositories'][0])
            with patch.object(team.time, 'monotonic', side_effect=[0, 100]):
                with self.assertRaisesRegex(fs.Conflict, 'deadline'):
                    team._download(self.lock['repositories'][0])

    def test_network_redirect_refused(self):
        with self.assertRaisesRegex(fs.Conflict, 'redirect'):
            team._NoRedirect().redirect_request(None, None, 302, '', {}, 'http://example.invalid')


class TeamManifestExportTests(unittest.TestCase):
    def test_export_preserves_nested_assets_and_removes_private_inventory_paths(self):
        from tools.export_team_manifest import export
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            library = root / 'private-library'
            skill = library / 'example--skills/skills/demo'
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_bytes(CONTENT)
            (skill / 'assets').mkdir()
            (skill / 'assets/example.bin').write_bytes(BINARY)
            (library / 'example--skills/LICENSE').write_bytes(b'Synthetic permissive license')
            inventory = root / 'inventory.json'
            inventory.write_bytes(fs.json_bytes({
                'library': str(library),
                'repositories': [{'repo': 'example/skills', 'url': 'https://github.com/example/skills', 'commit': COMMIT}],
                'skills': [{'repo': 'example/skills', 'name': 'demo', 'path': str(skill),
                            'entry_file': str(skill / 'SKILL.md'), 'sha256': fs.digest(CONTENT),
                            'active_paths': {'private': '/private/account/location'}}]}))
            lock = export(inventory)
            serialized = json.dumps(lock)
            self.assertNotIn(str(root), serialized)
            self.assertNotIn('/private/account', serialized)
            selected = {f['path']: f for f in lock['repositories'][0]['files']}
            self.assertEqual(selected['skills/demo/assets/example.bin']['sha256'], fs.digest(BINARY))
            self.assertIn('LICENSE', selected)
            (skill / 'SKILL.md').write_bytes(b'changed')
            with self.assertRaisesRegex(fs.Conflict, 'differs from inventory'):
                export(inventory)


    def test_export_uses_versioned_snapshot_folders_pins_only_shared_references_and_omits_listed_skills(self):
        from tools.export_team_manifest import export
        with tempfile.TemporaryDirectory() as temporary:
            library = Path(temporary).resolve() / 'private-library'
            skills = library / 'addyosmani--agent-skills-9.9.9'
            docs = library / 'upstash--context7'
            files = {skills / 'skills/demo/SKILL.md': CONTENT, skills / 'references/checklist.md': b'Checklist',
                     skills / 'commands/run.md': b'Command', skills / 'hooks/hook.sh': b'#!/bin/sh\n',
                     skills / 'scripts/tool.py': b'print()', skills / 'LICENSE': b'MIT', skills / 'README.md': b'Readme',
                     docs / 'skills/find-docs/SKILL.md': CONTENT, docs / 'skills/context7-mcp/SKILL.md': b'MCP skill',
                     docs / 'rules/context7-cli.md': b'Rule', docs / 'LICENSE': b'MIT'}
            for path, data in files.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            def skill(repo, root, name, data):
                entry = root / 'skills' / name / 'SKILL.md'
                return {'repo': repo, 'name': name, 'path': str(entry.parent), 'entry_file': str(entry), 'sha256': fs.digest(data)}
            inventory = Path(temporary).resolve() / 'inventory.json'
            inventory.write_bytes(fs.json_bytes({
                'library': str(library),
                'repositories': [
                    {'repo': 'addyosmani/agent-skills', 'url': 'https://github.com/addyosmani/agent-skills',
                     'commit': COMMIT, 'directory': str(skills)},
                    {'repo': 'upstash/context7', 'url': 'https://github.com/upstash/context7', 'commit': COMMIT[::-1]}],
                'skills': [skill('addyosmani/agent-skills', skills, 'demo', CONTENT),
                           skill('upstash/context7', docs, 'find-docs', CONTENT),
                           skill('upstash/context7', docs, 'context7-mcp', b'MCP skill')]}))
            lock = export(inventory)
            self.assertEqual((lock['bundle_count'], lock['eligible_bundle_count']), (2, 2))
            by_repo = {r['repository']: r for r in lock['repositories']}
            self.assertEqual({f['path'] for f in by_repo['addyosmani/agent-skills']['files']},
                             {'skills/demo/SKILL.md', 'references/checklist.md', 'LICENSE', 'README.md'})
            self.assertEqual([b['name'] for b in by_repo['upstash/context7']['bundles']], ['find-docs'])
            self.assertEqual({f['path'] for f in by_repo['upstash/context7']['files']}, {'skills/find-docs/SKILL.md', 'LICENSE'})
            self.assertNotIn(str(library), json.dumps(lock))


class PinnedTeamInventoryTests(unittest.TestCase):
    def test_inventory_is_portable_exact_and_limited(self):
        lock = team.manifest()
        self.assertEqual(lock['bundle_count'], 123)
        self.assertEqual(lock['eligible_bundle_count'], 119)
        self.assertEqual(len(lock['repositories']), 11)
        self.assertEqual(len(team.active_entries()), 9)
        summary = team.summary()
        self.assertEqual((summary['file_count'], summary['total_bytes']), (874, 21031577))
        self.assertEqual({x['name'] for x in lock['excluded']}, {'docx', 'pdf', 'pptx', 'xlsx'})
        serialized = json.dumps(lock)
        self.assertNotIn('/Users/', serialized)
        self.assertNotIn('Nio Knowledge', serialized)
        caveman = next(r for r in lock['repositories'] if r['repository'] == 'JuliusBrussee/caveman')
        self.assertFalse(any(f['path'].startswith(('engine/', 'proxy/', 'rewriter/')) for f in caveman['files']))
        for host in ['codex', 'claude', 'copilot']:
            entries = team.active_entries(host)
            self.assertEqual(len(entries), 9)
            self.assertIn({'codex': 'skill-codex.md', 'claude': 'skill.md', 'copilot': 'skill-copilot.md'}[host], entries['graphify']['path'])
            self.assertTrue(entries['context7']['path'].endswith('upstash--context7/skills/find-docs/SKILL.md'))
        for entry in team.active_entries().values():
            self.assertTrue(entry['path'].startswith(team.PREFIX + '/'))
        self.assertLess(team.summary()['total_bytes'], team.TOTAL_LIMIT)

    def test_graphify_agent_skills_and_context7_are_pinned_to_reviewed_commits(self):
        repos = {r['repository']: r for r in team.manifest()['repositories']}
        self.assertEqual(repos['Graphify-Labs/graphify']['commit'], '86c57be8204673c2a1b9849a3292a7dd3ab373d8')
        self.assertEqual(repos['addyosmani/agent-skills']['commit'], 'aeac41d4d005999432bb7312f7ff06383a91d59d')
        self.assertEqual(repos['upstash/context7']['commit'], 'e0041949fdb3b49b304d98715dde35be51b7c3d1')
        # Provider entry points exist in the pinned source; the private "prepared" copies are not upstream content.
        graphify = repos['Graphify-Labs/graphify']
        paths = {f['path'] for f in graphify['files']}
        self.assertTrue({'graphify/skill.md', 'graphify/skill-codex.md', 'graphify/skill-copilot.md', 'LICENSE', 'NOTICE'} <= paths)
        self.assertFalse(any(p.startswith('prepared/') for p in paths))
        agent_skills = repos['addyosmani/agent-skills']
        self.assertEqual(len(agent_skills['bundles']), 25)
        self.assertTrue(all(b['eligible'] and b['path'].startswith('skills/') for b in agent_skills['bundles']))
        self.assertTrue({'LICENSE', 'README.md'} <= {f['path'] for f in agent_skills['files']})
        for path in (f['path'] for f in agent_skills['files']):
            self.assertTrue(path in {'LICENSE', 'README.md'} or path.startswith(('skills/', 'references/')), path)
        self.assertTrue({'references/security-checklist.md', 'references/performance-checklist.md'}
                        <= {f['path'] for f in agent_skills['files']})
        context7 = repos['upstash/context7']
        self.assertEqual({b['name'] for b in context7['bundles']}, {'find-docs', 'context7-cli'})
        self.assertTrue(all(f['path'] in {'LICENSE', 'README.md'} or f['path'].startswith('skills/') for f in context7['files']))
        self.assertIn('skills/context7-cli/references/docs.md', {f['path'] for f in context7['files']})

    def test_only_nine_agent_skills_are_routed_and_lifecycle_skills_stay_named_only(self):
        from hae import skills
        routed = {name for rule in skills.routes().values() if rule.get('repository') == 'addyosmani/agent-skills'
                  for name in rule['candidates']}
        self.assertEqual(routed, {'security-and-hardening', 'performance-optimization', 'observability-and-instrumentation',
                                  'api-and-interface-design', 'ci-cd-and-automation', 'deprecation-and-migration',
                                  'documentation-and-adrs', 'source-driven-development', 'shipping-and-launch'})
        bundles = {b['name'] for r in team.manifest()['repositories'] if r['repository'] == 'addyosmani/agent-skills' for b in r['bundles']}
        self.assertEqual(len(bundles - routed), 16)
        self.assertFalse(any(rule.get('explicit_only') for task, rule in skills.routes().items() if task != 'karpathy'))
        self.assertFalse((bundles - routed) & {c for r in skills.routes().values() for c in r['candidates']})

if __name__ == '__main__':
    unittest.main()
