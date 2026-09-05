"""Integration boundaries tested only against temporary homes and mocked commands."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from backdrop.core import EXCLUDES, Library, apply_wallpaper, scan


class WallpaperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.library = Library(self.home)
        self.library.current.mkdir(parents=True)
        (self.library.current / 'theme.name').write_text('dracula\n')
        self.image = self.home / 'Pictures' / 'a wallpaper.png'
        self.image.parent.mkdir()
        self.image.write_bytes(b'fake image bytes')

    @patch('backdrop.core.subprocess.run')
    def test_apply_exact_argv(self, run: unittest.mock.Mock) -> None:
        result = apply_wallpaper(self.image, False, self.library)
        self.assertEqual(result, self.image)
        run.assert_called_once_with(['omarchy', 'theme', 'bg', 'set', str(self.image)],
                                    check=True, capture_output=True, text=True, timeout=30)
        self.assertNotIn('sudo', run.call_args.args[0])

    @patch('backdrop.core.subprocess.run')
    def test_pin_copies_before_apply(self, run: unittest.mock.Mock) -> None:
        def check_copy(argv: list[str], **kwargs: object) -> None:
            self.assertEqual(Path(argv[-1]).read_bytes(), self.image.read_bytes())
            self.assertEqual(Path(argv[-1]).parent, self.library.saved())
        run.side_effect = check_copy
        first = apply_wallpaper(self.image, True, self.library)
        second = apply_wallpaper(self.image, True, self.library)
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), self.image.read_bytes())
        self.assertEqual(run.call_args.args[0], ['omarchy', 'theme', 'bg', 'set', str(second)])

    @patch('backdrop.core.subprocess.run')
    def test_saved_file_is_not_duplicated(self, run: unittest.mock.Mock) -> None:
        saved = apply_wallpaper(self.image, True, self.library)
        self.assertEqual(apply_wallpaper(saved, True, self.library), saved)
        self.assertEqual(len(list(self.library.saved().iterdir())), 1)

    @patch('backdrop.core.subprocess.run')
    def test_missing_file_rejected(self, run: unittest.mock.Mock) -> None:
        with self.assertRaises(FileNotFoundError):
            apply_wallpaper(self.home / 'missing.png', True, self.library)
        run.assert_not_called()
        self.assertFalse(self.library.saved().exists())

    @patch('backdrop.core.subprocess.run')
    def test_unsupported_and_directories_rejected(self, run: unittest.mock.Mock) -> None:
        for suffix in ('.svg', '.tif', '.tiff'):
            path = self.home / ('bad' + suffix)
            path.touch()
            with self.assertRaises(ValueError):
                apply_wallpaper(path, False, self.library)
        with self.assertRaises(ValueError):
            apply_wallpaper(self.home, False, self.library)
        run.assert_not_called()

    @patch('backdrop.core.subprocess.run')
    def test_shell_metacharacters_are_literal(self, run: unittest.mock.Mock) -> None:
        path = self.home / '$(touch unsafe); space.png'
        path.touch()
        apply_wallpaper(path, False, self.library)
        self.assertEqual(run.call_args.args[0][-1], str(path))
        self.assertNotIn('shell', run.call_args.kwargs)

    @patch('backdrop.core.subprocess.run', side_effect=subprocess.CalledProcessError(1, ['omarchy']))
    def test_command_failure_propagates(self, run: unittest.mock.Mock) -> None:
        with self.assertRaises(subprocess.CalledProcessError):
            apply_wallpaper(self.image, False, self.library)

    @patch('backdrop.core.shutil.copyfileobj', side_effect=OSError('disk full'))
    @patch('backdrop.core.subprocess.run')
    def test_failed_copy_is_cleaned(self, run: unittest.mock.Mock, copy: unittest.mock.Mock) -> None:
        with self.assertRaises(OSError):
            apply_wallpaper(self.image, True, self.library)
        self.assertEqual(list(self.library.saved().iterdir()), [])
        run.assert_not_called()

    def test_scan_excludes_and_does_not_follow_loops(self) -> None:
        for name in EXCLUDES:
            directory = self.image.parent / name
            directory.mkdir()
            (directory / 'hidden.png').touch()
        nested = self.image.parent / 'Backdrops'
        nested.mkdir()
        included = nested / 'nice.JPG'
        included.touch()
        (nested / 'loop').symlink_to(self.image.parent, target_is_directory=True)
        (nested / 'bad.svg').touch()
        (nested / 'broken.png').symlink_to(self.home / 'missing')
        self.assertEqual(scan(self.image.parent, False), [self.image])
        self.assertEqual(set(scan(self.image.parent, True)), {self.image, included})

    def test_theme_slug_rejects_traversal(self) -> None:
        for slug in ('../escape', '.', '/tmp/evil', ''):
            (self.library.current / 'theme.name').write_text(slug)
            with self.assertRaises(ValueError):
                self.library.saved()

    def test_current_and_accent(self) -> None:
        self.assertIsNone(self.library.background())
        (self.library.current / 'background').symlink_to(self.image)
        self.assertEqual(self.library.background(), self.image)
        theme = self.library.current / 'theme'
        theme.mkdir()
        colors = theme / 'colors.toml'
        colors.write_text('accent = "#8be9fd"')
        self.assertEqual(self.library.accent(), '#8be9fd')
        colors.write_text('accent = "invalid CSS"')
        self.assertIsNone(self.library.accent())

    def test_source_paths(self) -> None:
        self.assertEqual(self.library.source('Agent Generated'), (self.image.parent / 'Agent_Generated', True))
        self.assertEqual(self.library.source('Saved'), (self.library.saved(), True))
        self.assertEqual(scan(self.home / 'missing', True), [])
