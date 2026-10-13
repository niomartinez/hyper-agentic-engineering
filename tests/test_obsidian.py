import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from hae import fs, obsidian


class ObsidianTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        self.vault = self.home / 'Vault with spaces & # symbols'
        self.vault.mkdir()

    def test_readiness_is_read_only_and_does_not_claim_running_or_enabled(self):
        before = list(self.home.rglob('*'))
        with patch.object(obsidian, '_app_path', return_value='/app/Obsidian'), patch.object(obsidian.shutil, 'which', return_value='/bin/obsidian'), patch.object(obsidian.subprocess, 'run') as run:
            result = obsidian.status(self.home, self.vault)
        self.assertTrue(result['app_detected'])
        self.assertTrue(result['cli_available'])
        self.assertEqual(result['app_running'], 'unverified')
        self.assertEqual(result['vault_registered'], 'unverified')
        self.assertFalse(result['memory_requires_obsidian'])
        run.assert_not_called()
        self.assertEqual(before, list(self.home.rglob('*')))

    def test_app_detection_uses_native_install_locations(self):
        cases = [('darwin', 'Applications/Obsidian.app'),
                 ('win32', 'AppData/Local/Obsidian/Obsidian.exe'),
                 ('linux', '.local/share/applications/obsidian.desktop')]
        for platform, relative in cases:
            with self.subTest(platform=platform):
                app = self.home / relative
                app.parent.mkdir(parents=True, exist_ok=True)
                app.touch()
                with patch.object(obsidian.sys, 'platform', platform), patch.object(obsidian.shutil, 'which', return_value=None):
                    self.assertEqual(obsidian.status(self.home, self.vault)['app_path'], str(app))

    def test_posix_openers_dispatch_manager_without_shell_or_vault_uri(self):
        for platform, opener in [('darwin', 'open'), ('linux', 'xdg-open')]:
            with self.subTest(platform=platform), patch.object(obsidian.sys, 'platform', platform), patch.object(obsidian, '_app_path', return_value='/app/Obsidian'), patch.object(obsidian.shutil, 'which', side_effect=lambda name: '/bin/' + name), patch.object(obsidian.subprocess, 'run') as run:
                result = obsidian.open_vault(self.home, self.vault)
                run.assert_called_once_with(['/bin/' + opener, 'obsidian://choose-vault'], check=True, capture_output=True, timeout=15)
                self.assertTrue(result['attempted'])
                self.assertFalse(result['vault_open_verified'])
                self.assertIn(str(self.vault), result['instructions'])

    def test_windows_opener_is_mocked(self):
        with patch.object(obsidian.sys, 'platform', 'win32'), patch.object(obsidian, '_app_path', return_value='Obsidian.exe'), patch.object(obsidian.shutil, 'which', return_value=None), patch.object(obsidian.os, 'startfile', create=True) as startfile:
            result = obsidian.open_vault(self.home, self.vault)
        startfile.assert_called_once_with('obsidian://choose-vault')
        self.assertFalse(result['vault_open_verified'])

    def test_missing_app_missing_vault_and_opener_error(self):
        with patch.object(obsidian, '_app_path', return_value=None), patch.object(obsidian.subprocess, 'run') as run:
            with self.assertRaisesRegex(fs.Conflict, 'not detected'):
                obsidian.open_vault(self.home, self.vault)
            run.assert_not_called()
        with self.assertRaisesRegex(fs.Conflict, 'does not exist'):
            obsidian.open_vault(self.home, self.home / 'Missing')
        with patch.object(obsidian.sys, 'platform', 'linux'), patch.object(obsidian, '_app_path', return_value='/app/obsidian'), patch.object(obsidian.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(fs.Conflict, 'opener unavailable'):
                obsidian.open_vault(self.home, self.vault)
        for error in [OSError('private output'), subprocess.CalledProcessError(1, ['open'], stderr='private output'), subprocess.TimeoutExpired(['open'], 15)]:
            with patch.object(obsidian.sys, 'platform', 'linux'), patch.object(obsidian, '_app_path', return_value='/app/obsidian'), patch.object(obsidian.shutil, 'which', return_value='/bin/xdg-open'), patch.object(obsidian.subprocess, 'run', side_effect=error):
                with self.assertRaisesRegex(fs.Conflict, 'opener failed') as raised:
                    obsidian.open_vault(self.home, self.vault)
                self.assertNotIn('private output', str(raised.exception))

    def test_linked_vault_and_non_directory_refused(self):
        linked = self.home / 'linked'
        try:
            linked.symlink_to(self.vault, target_is_directory=True)
        except OSError:
            self.skipTest('Symlinks unavailable')
        with self.assertRaises(fs.Conflict):
            obsidian.status(self.home, linked)
        file = self.home / 'file'
        file.touch()
        with self.assertRaisesRegex(fs.Conflict, 'not a directory'):
            obsidian.status(self.home, file)

    def test_starter_files_are_small_clean_and_portable(self):
        files = obsidian.vault_files()
        self.assertEqual([name for name, _ in files], ['Home.md', 'Practices/HAE Team.md', '.obsidian/app.json'])
        for name, data in files:
            self.assertFalse(Path(name).is_absolute())
            self.assertIsInstance(data, bytes)
            self.assertLess(len(data), 2000)
            self.assertNotIn(b'antoniomartinez', data)
        self.assertEqual(files[-1][1], b'{}\n')


if __name__ == '__main__':
    unittest.main()
