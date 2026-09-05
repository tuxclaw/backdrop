"""Verify decode policy without requiring the desktop's image-loader service."""
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from backdrop.imaging import decode, supported_extensions


class ImagingTests(unittest.TestCase):
    @patch('backdrop.imaging.GdkPixbuf.Pixbuf.new_from_file_at_scale')
    @patch('backdrop.imaging.GdkPixbuf.Pixbuf.get_file_info', return_value=(Mock(), 3200, 1800))
    def test_decode_is_bounded_and_reports_original_size(self, info: Mock, load: Mock) -> None:
        load.return_value.get_option.return_value = None
        thumbnail, resolution = decode(Path('/example/wide.png'), 480)
        load.assert_called_once_with('/example/wide.png', 480, 480, True)
        self.assertIs(thumbnail, load.return_value.apply_embedded_orientation.return_value)
        self.assertEqual(resolution, '3,200 × 1,800')

    @patch('backdrop.imaging.GdkPixbuf.Pixbuf.new_from_file_at_scale')
    @patch('backdrop.imaging.GdkPixbuf.Pixbuf.get_file_info', return_value=(Mock(), 3200, 1800))
    def test_rotated_dimensions(self, info: Mock, load: Mock) -> None:
        load.return_value.get_option.return_value = '6'
        _, resolution = decode(Path('/example/rotated.jpg'), 480)
        self.assertEqual(resolution, '1,800 × 3,200')

    @patch('backdrop.imaging.GdkPixbuf.Pixbuf.get_file_info', return_value=(None, 0, 0))
    def test_invalid_image_rejected(self, info: Mock) -> None:
        with self.assertRaises(ValueError):
            decode(Path('/example/corrupt.png'), 480)

    def test_formats_are_supported_wallpaper_types(self) -> None:
        self.assertIn('.png', supported_extensions())
        self.assertNotIn('.svg', supported_extensions())
        self.assertNotIn('.tiff', supported_extensions())
