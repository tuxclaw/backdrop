## [2026-09-05] Omarchy wallpaper API
**By:** Sonic

- Apply: `omarchy theme bg set <path>` → `omarchy-theme-bg-set`. Symlinks `~/.local/state/omarchy/current/background` and IPC `omarchy-shell -q background set "$BACKGROUND"`.
- Stock gallery: `omarchy theme bg-switcher` / Super+Ctrl+Space. Sources: `~/.local/state/omarchy/current/theme/backgrounds` + `~/.config/omarchy/backgrounds/$theme_name`.
- Theme slug file: `~/.local/state/omarchy/current/theme.name` (currently `dracula`).
- User extras dir is empty: `~/.config/omarchy/backgrounds/dracula/`.
- Never edit `/usr/share/omarchy/`. Never sudo. Never rebind Super+Ctrl+Space.
- Menu apply path: `background=$(omarchy-theme-bg-switcher); [[ -n $background ]] && omarchy-theme-bg-set "$background"`.

## [2026-09-05] Pictures
**By:** Sonic

- Lots of wallpapers in `/home/tux/Pictures` (54 top-level images plus dirs: Agent_Generated, alienware-wallpapers, Backdrops, Dracula, …).
- Exclude by default: Screenshots, Phone, Icons_Logos, GitKraken, Jetbrains, veteran_site.
- Skip huge/non-desktop types as apply targets: `.tif`, `.svg` (thumbnail ok if cheap, do not set SVG/TIF as wallpaper).
- Current wallpaper: `/home/tux/.local/state/omarchy/current/theme/backgrounds/base.png` (label Base).

## [2026-09-05] Black All-wallpapers grid
**By:** Sonic
Live window 10:29 PDT: 822 items, **preview works** (Debian.png 3840×2160 visible). Grid is empty black with a thin cyan selected bar and a scrollbar. Cause: Gtk.GridView cards collapse to ~0 height. Overlay only set `width_request=180`; no height. AspectFrame cannot compute 16:9 without a width allocation. Inspector preview has `width_request=280` so it paints. Not a decode bug. Fix: explicit 16:9 size_request on each card (e.g. 180×101 or larger), do not let Picture `can_shrink` collapse the tile. Reinstall `scripts/install.py` after the patch — live app is `~/.local/share/backdrop`.

## [2026-09-05] Build and validation — Tails

- Runtime uses stdlib + system GI only. No pip install or network requests were made.
- System Python has no pytest. Created an ignored `.venv` with system site packages,
  and copied pytest 9.0.2 plus its local dependencies (pluggy, iniconfig, packaging,
  pygments, py.py) from the existing crypto-trader virtual environment. These are
  test-only dependencies, needed for the requested `python -m pytest` acceptance.
- GridView maps trigger 480px thumbnail jobs. Three workers, 96-thumbnail LRU-style
  cache; 1000px previews. Pending obsolete previews and unmapped thumbnail jobs are
  cancelled when possible. Running decoders finish in the background.
- All means Pictures recursive; Theme and Saved are explicit separate sources.
  Directory symlinks and hidden entries are skipped. File symlinks are resolved and
  deduplicated. Refresh is manual; reopening picks up current theme accent changes.
- The current badge follows the actual resolved file; pinning creates a separate
  copy, which is marked in Saved rather than its Pictures original.
- Sandbox approval rejected git initialization, display access, real image-loader
  test access, and installation under ~/.local. Do not claim these steps completed.
  GUI layout remains visually unverified. Prepared installer works in staging.
