#!/usr/bin/env python3
"""Install a relocatable user copy with no package manager or network access."""
from pathlib import Path
import argparse
import shlex
import shutil


def install(home: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    app = home / '.local/share/backdrop'
    app.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root / 'src/backdrop', app / 'backdrop', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    launcher = home / '.local/bin/backdrop'
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text('#!/bin/sh\nexec /usr/bin/python3 -c ' + shlex.quote(
        'import sys; sys.path.insert(0, ' + repr(str(app)) + '); from backdrop.app import main; raise SystemExit(main())'
    ) + ' "$@"\n')
    launcher.chmod(0o755)
    desktop = home / '.local/share/applications/io.github.tuxclaw.Backdrop.desktop'
    desktop.parent.mkdir(parents=True, exist_ok=True)
    # Desktop Exec quoting is distinct from shell quoting.
    escaped = str(launcher).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    desktop.write_text((root / 'data/io.github.tuxclaw.Backdrop.desktop').read_text().replace('Exec=backdrop', f'Exec="{escaped}"'))
    icon = home / '.local/share/icons/hicolor/scalable/apps/io.github.tuxclaw.Backdrop.svg'
    icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / 'data/io.github.tuxclaw.Backdrop.svg', icon)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home(), help='Installation home (also supports staging)')
    install(parser.parse_args().home.expanduser().resolve())


if __name__ == '__main__':
    main()
