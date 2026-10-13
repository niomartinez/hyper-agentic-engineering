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
                 (prefix + 'unrelated/link', b'../../outside', stat.S_IFLNK),
                 (prefix + 'skills/demo/SKILL.md', CONTENT, stat.S_IFREG),
                 (prefix + 'unrelated/COn.txt', b'x', stat.S_IFREG),
                 (prefix + 'unrelated/x\\y', b'x', stat.S_IFREG)]
        for extra in cases:
            with self.subTest(name=extra[0]):
                with self.assertRaises(fs.Conflict):
                    team._archive_files(self.lock['repositories'][0], archive_bytes(extra=extra))

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


class PinnedTeamInventoryTests(unittest.TestCase):
    def test_inventory_is_portable_exact_and_limited(self):
        lock = team.manifest()
        self.assertEqual(lock['bundle_count'], 96)
        self.assertEqual(lock['eligible_bundle_count'], 92)
        self.assertEqual(len(lock['repositories']), 9)
        self.assertEqual(len(team.active_entries()), 8)
        self.assertEqual({x['name'] for x in lock['excluded']}, {'docx', 'pdf', 'pptx', 'xlsx'})
        serialized = json.dumps(lock)
        self.assertNotIn('/Users/', serialized)
        self.assertNotIn('Nio Knowledge', serialized)
        caveman = next(r for r in lock['repositories'] if r['repository'] == 'JuliusBrussee/caveman')
        self.assertFalse(any(f['path'].startswith(('engine/', 'proxy/', 'rewriter/')) for f in caveman['files']))
        for host in ['codex', 'claude', 'copilot']:
            entries = team.active_entries(host)
            self.assertEqual(len(entries), 8)
            self.assertIn({'codex': 'skill-codex.md', 'claude': 'skill.md', 'copilot': 'skill-copilot.md'}[host], entries['graphify']['path'])
        for entry in team.active_entries().values():
            self.assertTrue(entry['path'].startswith(team.PREFIX + '/'))
        self.assertLess(team.summary()['total_bytes'], team.TOTAL_LIMIT)


if __name__ == '__main__':
    unittest.main()
