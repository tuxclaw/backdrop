# Backdrop

A dark, focused wallpaper gallery for Omarchy. Browse Pictures, search by filename,
preview your selection, and give your desktop a fresh view.

Backdrop is the **Pictures picker**. **Super+Ctrl+Space still works** as Omarchy's
stock theme gallery. “Save to theme” is on by default: applying keeps a copy in
`~/.config/omarchy/backgrounds/<current-theme>/`, making it available there too.
Turn the switch off to apply the original without keeping a copy.

## Launch and install

Requires Python 3.11+, PyGObject, GTK 4.12+ and libadwaita 1.4+ (available on this
Omarchy installation). No runtime pip packages, network access, or wallpaper daemon.

From this project:

```sh
python -m backdrop
```

Install a standalone user copy, launcher, desktop entry, and icon:

```sh
python scripts/install.py
~/.local/bin/backdrop
```

Search **Backdrop** in Familiar. The desktop entry uses an absolute launcher path,
so it also works when Familiar's PATH omits `~/.local/bin`. Re-run the installer
after changes; the installed copy does not depend on the project staying in place.
For a preview of the installation files, use `--home /tmp/backdrop-staging`.

## Use

- Choose a collection on the left; narrow windows have a sidebar toggle.
- Click a card to preview. Arrow keys navigate the focused grid.
- Double-click or press Enter to apply. Escape closes. Ctrl+F focuses search.
- Refresh rescans the collection, current theme, and current wallpaper.
- A current badge identifies the resolved wallpaper file. A saved copy is a distinct
  file, so its badge appears in Saved rather than on its Pictures original.

All recursively scans `~/Pictures`; Pictures lists only top-level files. Dedicated
sources cover Agent_Generated, Backdrops, Dracula, the active Theme, and Saved.
Scans omit Screenshots, Phone, Icons_Logos, GitKraken, Jetbrains, veteran_site,
hidden folders/files, and directory symlinks. Missing folders have an empty state.
PNG, JPEG, WebP and AVIF appear when supported by the installed Pixbuf loaders.
Unreadable images are removed as their thumbnails load; SVG and TIFF are excluded.

Thumbnails load when cards map, with three background workers and a 96-image
memory cache. Thumbnail outputs are bounded to 480 pixels; previews to 1000.
Some codecs can still require larger internal buffers during decoding. Scanning,
image decoding, copying, and commands run outside GTK's UI thread. Preview shows
the whole image; the gallery uses a 16:9 crop. Omarchy controls desktop rendering.

Applying only invokes `omarchy theme bg set <absolute-path>`. Saving uses exclusive,
collision-safe filenames, and reapplying a file already in Saved reuses it. A copy
is retained if Omarchy reports failure, so it remains available for retry.
No packaged Omarchy files, bindings, or other desktop configuration are edited.

## Tests

A local `.venv` was prepared offline with system GI access and pytest. Activate it:

```sh
. .venv/bin/activate
python -m pytest
```

The test suite mocks every wallpaper command and image-loader boundary. It checks
exact argv, copy-before-apply, collisions, failure cleanup, missing/unsupported
files, safe scanning, theme validation, and bounded orientation-aware decoding.
It never applies a live wallpaper. Standard-library core tests also run with
`python -m unittest discover -s tests`.

The `.venv` is not part of source control. On another machine, supply pytest in a
Python environment with system site packages enabled; the application needs only
stdlib and GI. GUI smoke testing requires access to the desktop display and its
local image-loader service.
