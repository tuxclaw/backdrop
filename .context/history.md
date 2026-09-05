## [2026-09-05] Scaffold
**Agent:** Sonic
**Branch:** (pending Tails `andy/picker`)
**Changes:** Seeded `.context/` and dispatched Tails (ACP Codex `gpt-6-astra`) to build the picker.
**Files:** `.context/decisions.md`, `.context/notes.md`, `.context/history.md`
**Commit:** none yet

## [2026-09-05] Implement Backdrop — Tails
**Agent:** Tails (sole builder; no delegation)
**Branch:** blocked; initializing `andy/picker` was rejected by the approval system
because the workspace's `.git` is read-only. No main branch touched, no push.
**Changes:** Implemented dark GTK4/libadwaita Pictures picker, seven sidebar sources,
filename search, responsive GridView, rounded thumbnail overlays and current badge,
large preview, default-on Save to theme switch, suggested Apply button, toast status,
keyboard navigation, Enter/double-click apply, Escape close, and theme accent CSS.
Added asynchronous scanning/decoding/copy/apply, bounded thumbnail cache and preview
sizes, supported-format filtering, excludes, loop avoidance, collision-safe copies,
and the exact Omarchy command wrapper.
**Files:** `src/backdrop/{__init__.py,__main__.py,core.py,imaging.py,app.py,style.css}`,
root `backdrop` symlink for module launch, `tests/test_core.py`,
`tests/test_imaging.py`, `data/io.github.tuxclaw.Backdrop.desktop`,
`data/io.github.tuxclaw.Backdrop.svg`, `scripts/install.py`, `pyproject.toml`,
`.gitignore`, `README.md`, and appended context notes/history.
**Validation:** 16 pytest tests passed in the offline `.venv`; one upstream GI
GLib deprecation warning. Every apply command mocked; decoder policy unit tests
mocked. Real Pixbuf test was blocked by sandbox D-Bus restrictions and its escalation
was rejected. Python compilation, GTK property introspection, staged desktop-file
validation, SVG XML parsing, and launcher shell syntax checks passed.
**Launch:** `python -m backdrop` attempted. Sandbox denied access to the desktop;
request for GUI smoke-test access was rejected. No mapped-window or visual check
could be completed. Added a clear nonzero exit for unavailable displays.
**Install:** Complete installer staged at `/tmp/backdrop-install-check`; actual
`python scripts/install.py` request was rejected because ~/.local is outside the
writable workspace. Desktop entry is NOT installed in Tux's live applications dir.
**Wallpaper:** No live wallpaper change or smoke-apply performed.
**Commit:** none; git write approval rejected.
**Remaining acceptance:** Run GUI smoke/visual checks, install with
`python scripts/install.py`, initialize `andy/picker`, and commit imperatively when
filesystem/display permissions are available.

## [2026-09-05] Verify + install — Sonic
**Agent:** Sonic
**Branch:** (init pending this step)
**Changes:** Host pytest 16 passed. Installed user launcher + desktop + icon. Reviewing apply path: argv is `omarchy theme bg set`, no shell, no sudo.
**Files:** `~/.local/bin/backdrop`, `~/.local/share/applications/io.github.tuxclaw.Backdrop.desktop`
**Commit:** pending

## [2026-09-05] Fix collapsed All-wallpapers grid — Tails
**Agent:** Tails (sole builder; no delegation)
**Branch:** `andy/picker`
**Changes:** Give each grid card an explicit 240×135 minimum size before its
thumbnail loads, plus 135px CSS minimum heights on cards and gallery children.
Retain AspectFrame 16:9 cover cropping and GridView's 2–6 column limits. Picture
can still shrink within the reserved tile without collapsing its outer minimum.
Preview, decoding, scanning, apply, and Omarchy integration are unchanged.
**Files:** `src/backdrop/app.py`, `src/backdrop/style.css`, `.context/history.md`.
**Validation:** `.venv/bin/python -m pytest`: 16 passed, one existing GI
deprecation warning. `git diff --check` passed. Live GUI appearance remains
unverified; Sonic should check the gallery after reinstalling.
**Install:** Skipped as requested: ~/.local is outside the sandbox writable roots.
Sonic will reinstall with `python scripts/install.py`.
**Wallpaper:** No live wallpaper change.
**Commit:** Not attempted because the active filesystem policy explicitly makes
this repository's `.git` read-only. Patch is ready on `andy/picker`; pre-existing
changes to `.context/notes.md` and `.context/.active-agent` were left untouched.
