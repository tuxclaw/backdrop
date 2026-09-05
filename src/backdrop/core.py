"""Filesystem discovery and the single Omarchy wallpaper boundary."""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib

EXTENSIONS = frozenset({'.png', '.jpg', '.jpeg', '.webp', '.avif'})
EXCLUDES = frozenset({'Screenshots', 'Phone', 'Icons_Logos', 'GitKraken', 'Jetbrains', 'veteran_site'})


class Library:
    def __init__(self, home: Path | None = None) -> None:
        self.home = home or Path.home()
        self.pictures = self.home / 'Pictures'
        self.current = self.home / '.local/state/omarchy/current'

    def theme_slug(self) -> str:
        slug = (self.current / 'theme.name').read_text().strip()
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', slug):
            raise ValueError('The current theme name is invalid.')
        return slug

    def saved(self) -> Path:
        return self.home / '.config/omarchy/backgrounds' / self.theme_slug()

    def background(self) -> Path | None:
        try:
            return (self.current / 'background').resolve(strict=True)
        except (OSError, RuntimeError):
            return None

    def accent(self) -> str | None:
        try:
            color = tomllib.loads((self.current / 'theme/colors.toml').read_text()).get('accent')
            return color if isinstance(color, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', color) else None
        except (OSError, ValueError):
            return None

    def source(self, name: str) -> tuple[Path, bool]:
        if name == 'All':
            return self.pictures, True
        if name == 'Pictures':
            return self.pictures, False
        if name == 'Theme':
            return self.current / 'theme/backgrounds', True
        if name == 'Saved':
            return self.saved(), True
        return self.pictures / name.replace('Agent Generated', 'Agent_Generated'), True


def scan(root: Path, recursive: bool, extensions: frozenset[str] = EXTENSIONS) -> list[Path]:
    """Walk only the selected source; never descend into directory symlinks."""
    found: list[Path] = []
    seen: set[Path] = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDES and not d.startswith('.')) if recursive else []
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix.lower() not in extensions or name.startswith('.'):
                continue
            try:
                resolved = path.resolve(strict=True)
                if resolved not in seen and resolved.is_file() and os.access(resolved, os.R_OK):
                    found.append(path.absolute())
                    seen.add(resolved)
            except (OSError, RuntimeError):
                continue
    return sorted(found, key=lambda p: (p.name.casefold(), str(p)))


def apply_wallpaper(path: Path, save: bool, library: Library) -> Path:
    """Optionally keep a collision-safe copy, then let Omarchy apply it."""
    path = path.expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError('Choose an image file.')
    if path.suffix.lower() not in EXTENSIONS:
        raise ValueError('This image format cannot be used as a wallpaper.')
    target = path
    if save:
        extras = library.saved()
        extras.mkdir(parents=True, exist_ok=True)
        if path.parent != extras.resolve():
            # Exclusive creation prevents concurrent saves from overwriting a file.
            fd, filename = tempfile.mkstemp(prefix=path.stem[:100] + '-', suffix=path.suffix.lower(), dir=extras)
            target = Path(filename)
            try:
                with os.fdopen(fd, 'wb') as destination, path.open('rb') as source:
                    shutil.copyfileobj(source, destination)
            except BaseException:
                target.unlink(missing_ok=True)
                raise
    subprocess.run(['omarchy', 'theme', 'bg', 'set', str(target)], check=True, capture_output=True, text=True, timeout=30)
    return target
