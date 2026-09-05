## [2026-09-05] Backdrop — Omarchy wallpaper picker
**By:** Sonic
**Context:** Tux cannot easily pick wallpapers from `~/Pictures`. Stock Omarchy already sets wallpaper; Super+Ctrl+Space only shows theme + extras folders. Do not invent a wallpaper engine.
**Decision:** Build `backdrop`, a polished GTK4/libadwaita picker that wraps `omarchy theme bg set`. Optional pin copies into `~/.config/omarchy/backgrounds/<theme-slug>/` so the stock switcher keeps the image.
**Alternatives considered:** Gravitywell toy (rejected — not useful). Competing wallpaper daemon / hyprpaper GUI (rejected — fights Omarchy). Aether (theme generator, not a Pictures picker). Quickshell overlay (rejected for v1 — want a launcher app).
**Status:** Active

## [2026-09-05] Stack
**By:** Sonic
**Context:** gtk4, libadwaita, python-gobject already installed. Familiar uses GNOME profile. Library: `/home/tux/Documents/docs/library/gtk/python-gtk.md`.
**Decision:** Python 3 + PyGObject + GTK 4 + libadwaita. App id `io.github.tuxclaw.Backdrop`. Project `/home/tux/Documents/Projects/backdrop`.
**Status:** Active
