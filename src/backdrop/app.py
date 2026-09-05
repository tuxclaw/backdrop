"""The Backdrop GTK interface. Workers return data; only GTK's thread touches UI."""
from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
import logging
import subprocess
from typing import Callable, Any

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango

from backdrop.core import Library, apply_wallpaper, scan
from backdrop.imaging import decode, supported_extensions

SOURCES = [('All', 'view-grid-symbolic'), ('Pictures', 'folder-pictures-symbolic'),
           ('Agent Generated', 'starred-symbolic'), ('Backdrops', 'image-x-generic-symbolic'),
           ('Dracula', 'weather-clear-night-symbolic'), ('Theme', 'applications-graphics-symbolic'),
           ('Saved', 'bookmark-new-symbolic')]


def label(text: str, css: str = '', **kwargs: Any) -> Gtk.Label:
    widget = Gtk.Label(label=text, xalign=0, **kwargs)
    if css:
        widget.add_css_class(css)
    return widget


def vertical(spacing: int = 0) -> Gtk.Box:
    return Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)


class Wallpaper(GObject.Object):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self.dimensions = 'Loading image…'


class Window(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application) -> None:
        super().__init__(application=application, title='Backdrop', default_width=1100, default_height=720)
        self.set_size_request(650, 560)
        self.add_css_class('backdrop')
        self.library = Library()
        self.current = self.library.background()
        self.pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix='backdrop')
        self.cache: OrderedDict[Path, tuple[Any, str]] = OrderedDict()
        self.closed = False
        self.busy = False
        self.generation = 0
        self.selected: Wallpaper | None = None
        self.preview_pending: Future | None = None
        self.source_name = 'All'
        self.items: list[Wallpaper] = []
        self.install_style()
        self.toast = Adw.ToastOverlay()
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.search = Gtk.SearchEntry(placeholder_text='Search wallpapers', width_request=280)
        self.search.connect('search-changed', self.filter_changed)
        self.search.connect('activate', self.apply_selected)
        header.set_title_widget(self.search)
        header.pack_start(label('Backdrop', 'title'))
        refresh = Gtk.Button(icon_name='view-refresh-symbolic', tooltip_text='Refresh collection')
        refresh.connect('clicked', self.refresh)
        header.pack_end(refresh)
        toolbar.add_top_bar(header)
        self.split = Adw.OverlaySplitView(min_sidebar_width=190, max_sidebar_width=190)
        sidebar = vertical(20)
        sidebar.add_css_class('sources')
        heading = label('YOUR COLLECTION', 'eyebrow')
        heading.set_margin_start(12)
        sidebar.append(heading)
        self.sources = Gtk.ListBox()
        self.sources.add_css_class('navigation-sidebar')
        for name, icon in SOURCES:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(spacing=12)
            box.append(Gtk.Image(icon_name=icon))
            box.append(label(name))
            row.set_child(box)
            self.sources.append(row)
        sidebar.append(self.sources)
        spacer = Gtk.Box(vexpand=True)
        sidebar.append(spacer)
        sidebar.append(label('A fresh point of view.', 'hint'))
        self.split.set_sidebar(sidebar)
        content = vertical()
        intro = vertical(4)
        for side in ('top', 'bottom', 'start', 'end'):
            getattr(intro, f'set_margin_{side}')(24 if side != 'bottom' else 8)
        intro.append(label('MAKE ROOM FOR INSPIRATION', 'eyebrow'))
        self.collection_title = label('All wallpapers', 'collection-title')
        intro.append(self.collection_title)
        self.count = label('Finding your next backdrop…', 'dim-label')
        intro.append(self.count)
        content.append(intro)
        self.store = Gio.ListStore.new(Wallpaper)
        self.selection = Gtk.SingleSelection(model=self.store)
        self.selection.connect('notify::selected-item', self.selection_changed)
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', self.setup_card)
        factory.connect('bind', self.bind_card)
        factory.connect('unbind', self.unbind_card)
        self.grid = Gtk.GridView(model=self.selection, factory=factory, min_columns=2, max_columns=6,
                                 single_click_activate=False, hexpand=True, vexpand=True)
        self.grid.add_css_class('gallery')
        self.grid.connect('activate', self.activate_item)
        self.stack = Gtk.Stack(vexpand=True)
        self.stack.add_named(Gtk.ScrolledWindow(child=self.grid, hscrollbar_policy=Gtk.PolicyType.NEVER), 'grid')
        self.empty = Adw.StatusPage(icon_name='folder-pictures-symbolic', title='A little room for possibility',
                                   description='Add images to this folder to find them here.')
        self.stack.add_named(self.empty, 'empty')
        content.append(self.stack)
        content.append(self.build_inspector())
        self.split.set_content(content)
        toolbar.set_content(self.split)
        self.toast.set_child(toolbar)
        self.set_content(self.toast)
        menu = Gtk.ToggleButton(icon_name='sidebar-show-symbolic', tooltip_text='Show collections', visible=False)
        menu.bind_property('active', self.split, 'show-sidebar', GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE)
        header.pack_start(menu)
        breakpoint = Adw.Breakpoint(condition=Adw.BreakpointCondition.parse('max-width: 900px'))
        breakpoint.add_setter(self.split, 'collapsed', True)
        breakpoint.add_setter(self.split, 'show-sidebar', False)
        breakpoint.add_setter(menu, 'visible', True)
        self.add_breakpoint(breakpoint)
        keys = Gtk.EventControllerKey()
        keys.connect('key-pressed', self.key_pressed)
        self.add_controller(keys)
        self.connect('close-request', self.close_requested)
        self.sources.connect('row-selected', self.source_changed)
        self.sources.select_row(self.sources.get_row_at_index(0))

    def install_style(self) -> None:
        css = Path(__file__).with_name('style.css').read_text()
        accent = self.library.accent()
        if accent:
            css = (f'@define-color accent_bg_color {accent}; @define-color accent_color {accent}; '
                   '@define-color accent_fg_color #15151e; '
                   f':root {{ --accent-bg-color: {accent}; --accent-color: {accent}; --accent-fg-color: #15151e; }}\n') + css
        provider = Gtk.CssProvider()
        provider.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def build_inspector(self) -> Gtk.Box:
        panel = Gtk.Box(spacing=24)
        panel.add_css_class('inspector')
        self.preview = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN, can_shrink=True)
        frame = Gtk.AspectFrame(ratio=16 / 9, obey_child=False, child=self.preview, width_request=280)
        frame.set_overflow(Gtk.Overflow.HIDDEN)
        frame.add_css_class('preview')
        panel.append(frame)
        details = vertical(8)
        details.set_hexpand(True)
        details.append(label('PREVIEW', 'eyebrow'))
        self.filename = label('Choose a wallpaper', 'title-3', ellipsize=Pango.EllipsizeMode.MIDDLE)
        details.append(self.filename)
        self.metadata = label('Your next view starts here.', 'dim-label')
        details.append(self.metadata)
        save_row = Gtk.Box(spacing=12)
        save_row.append(label('Save to theme', hexpand=True))
        self.save = Gtk.Switch(active=True, valign=Gtk.Align.CENTER, tooltip_text='Keep a copy for Super+Ctrl+Space')
        save_row.append(self.save)
        details.append(save_row)
        actions = Gtk.Box(spacing=16)
        self.apply_button = Gtk.Button(label='Apply wallpaper', sensitive=False)
        self.apply_button.add_css_class('suggested-action')
        self.apply_button.add_css_class('pill')
        self.apply_button.add_css_class('apply')
        self.apply_button.connect('clicked', self.apply_selected)
        actions.append(self.apply_button)
        actions.append(label('↵ Apply · Esc Close', 'hint'))
        details.append(actions)
        panel.append(details)
        return panel

    def submit(self, work: Callable[[], Any], done: Callable[[Any, Exception | None], None]) -> Future:
        future = self.pool.submit(work)

        def completed(result: Future) -> None:
            if result.cancelled():
                return
            try:
                value, error = result.result(), None
            except Exception as exc:
                value, error = None, exc
            GLib.idle_add(deliver, value, error)

        def deliver(value: Any, error: Exception | None) -> bool:
            if not self.closed:
                done(value, error)
            return GLib.SOURCE_REMOVE

        future.add_done_callback(completed)
        return future

    def setup_card(self, factory: Gtk.SignalListItemFactory, item: Gtk.ListItem) -> None:
        picture = Gtk.Picture(content_fit=Gtk.ContentFit.COVER, can_shrink=True)
        frame = Gtk.AspectFrame(ratio=16 / 9, obey_child=False, child=picture)
        overlay = Gtk.Overlay(child=frame, width_request=180)
        overlay.set_overflow(Gtk.Overflow.HIDDEN)
        overlay.add_css_class('wallpaper-card')
        caption = vertical(2)
        caption.set_valign(Gtk.Align.END)
        caption.add_css_class('caption')
        title = label('', ellipsize=Pango.EllipsizeMode.MIDDLE)
        dimensions = label('', 'dim-label')
        caption.append(title)
        caption.append(dimensions)
        overlay.add_overlay(caption)
        badge = label('✓ CURRENT', 'badge', halign=Gtk.Align.START, valign=Gtk.Align.START, visible=False)
        overlay.add_overlay(badge)
        item.set_child(overlay)
        item.parts = (picture, title, dimensions, badge)
        item.wallpaper = None
        item.pending = None
        overlay.connect('map', self.card_mapped, item)
        overlay.connect('unmap', self.card_unmapped, item)

    def bind_card(self, factory: Gtk.SignalListItemFactory, item: Gtk.ListItem) -> None:
        wallpaper = item.get_item()
        item.wallpaper = wallpaper
        picture, title, dimensions, badge = item.parts
        picture.set_paintable(None)
        title.set_label(wallpaper.path.name)
        dimensions.set_label(wallpaper.dimensions)
        badge.set_visible(wallpaper.path.resolve() == self.current)
        item.get_child().set_tooltip_text(wallpaper.path.name)
        if item.get_child().get_mapped():
            self.card_mapped(item.get_child(), item)

    def unbind_card(self, factory: Gtk.SignalListItemFactory, item: Gtk.ListItem) -> None:
        self.card_unmapped(item.get_child(), item)
        item.wallpaper = None
        item.parts[0].set_paintable(None)

    def card_unmapped(self, widget: Gtk.Widget, item: Gtk.ListItem) -> None:
        if item.pending:
            item.pending.cancel()
            item.pending = None

    def card_mapped(self, widget: Gtk.Widget, item: Gtk.ListItem) -> None:
        wallpaper = item.wallpaper
        if wallpaper is None:
            return

        def ready(value: Any, error: Exception | None) -> None:
            if error:
                self.remove_unreadable(wallpaper)
                return
            self.cache[wallpaper.path] = value
            self.cache.move_to_end(wallpaper.path)
            while len(self.cache) > 96:
                self.cache.popitem(last=False)
            wallpaper.dimensions = value[1]
            if item.wallpaper is wallpaper:
                item.parts[0].set_paintable(Gdk.Texture.new_for_pixbuf(value[0]))
                item.parts[2].set_label(value[1])

        cached = self.cache.get(wallpaper.path)
        if cached:
            ready(cached, None)
        else:
            item.pending = self.submit(lambda: decode(wallpaper.path, 480), ready)

    def remove_unreadable(self, wallpaper: Wallpaper) -> None:
        if wallpaper in self.items:
            self.items.remove(wallpaper)
        found, index = self.store.find(wallpaper)
        if found:
            self.store.remove(index)
        self.update_count()

    def source_changed(self, box: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row:
            self.source_name = SOURCES[row.get_index()][0]
            if self.split.get_collapsed():
                self.split.set_show_sidebar(False)
            self.refresh()

    def refresh(self, *_args: Any) -> None:
        self.generation += 1
        generation = self.generation
        self.current = self.library.background()
        self.cache.clear()
        self.items = []
        self.store.remove_all()
        self.collection_title.set_label('All wallpapers' if self.source_name == 'All' else self.source_name)
        self.count.set_label('Finding your next backdrop…')
        self.empty.set_title('Gathering your collection')
        self.empty.set_description('A fresh view is on its way.')
        self.stack.set_visible_child_name('empty')
        source_name = self.source_name

        def work() -> list[Path]:
            root, recursive = self.library.source(source_name)
            return scan(root, recursive, supported_extensions())

        def ready(paths: list[Path] | None, error: Exception | None) -> None:
            if generation != self.generation:
                return
            if error:
                self.notify(str(error))
            self.items = [Wallpaper(path) for path in paths or []]
            self.filter_changed()

        self.submit(work, ready)

    def filter_changed(self, *_args: Any) -> None:
        query = self.search.get_text().casefold().strip()
        selected_path = self.selected.path if self.selected else None
        filtered = [item for item in self.items if query in item.path.name.casefold()]
        self.store.splice(0, self.store.get_n_items(), filtered)
        for index, item in enumerate(filtered):
            if item.path == selected_path:
                self.selection.set_selected(index)
                break
        self.update_count()

    def update_count(self) -> None:
        count = self.store.get_n_items()
        self.count.set_label(f'{count} wallpaper' + ('' if count == 1 else 's') + ' · Find your next view')
        self.empty.set_title('No matches' if self.search.get_text() else 'A little room for possibility')
        self.empty.set_description('Try a different filename.' if self.search.get_text() else 'Add images to this folder to find them here.')
        self.stack.set_visible_child_name('grid' if count else 'empty')

    def selection_changed(self, *_args: Any) -> None:
        if self.preview_pending:
            self.preview_pending.cancel()
        self.selected = self.selection.get_selected_item()
        self.preview.set_paintable(None)
        self.apply_button.set_sensitive(False)
        wallpaper = self.selected
        if wallpaper is None:
            self.filename.set_label('Choose a wallpaper')
            self.metadata.set_label('Your next view starts here.')
            return
        self.filename.set_label(wallpaper.path.name)
        self.filename.set_tooltip_text(str(wallpaper.path))
        self.metadata.set_label('Loading preview…')

        def ready(value: Any, error: Exception | None) -> None:
            if self.selected is not wallpaper:
                return
            if error:
                self.remove_unreadable(wallpaper)
                return
            wallpaper.dimensions = value[1]
            self.preview.set_paintable(Gdk.Texture.new_for_pixbuf(value[0]))
            self.metadata.set_label(value[1] + (' · Current wallpaper' if wallpaper.path.resolve() == self.current else ''))
            self.apply_button.set_sensitive(not self.busy)

        self.preview_pending = self.submit(lambda: decode(wallpaper.path, 1000), ready)

    def activate_item(self, grid: Gtk.GridView, position: int) -> None:
        self.selection.set_selected(position)
        self.apply_selected()

    def apply_selected(self, *_args: Any) -> None:
        if self.selected is None or self.busy:
            return
        wallpaper, save = self.selected, self.save.get_active()
        self.busy = True
        self.apply_button.set_sensitive(False)
        self.apply_button.set_label('Applying…')

        def work() -> Path:
            decode(wallpaper.path, 32)
            return apply_wallpaper(wallpaper.path, save, self.library)

        def ready(target: Path | None, error: Exception | None) -> None:
            self.busy = False
            self.apply_button.set_label('Apply wallpaper')
            self.apply_button.set_sensitive(self.selected is not None)
            if error:
                detail = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
                self.notify('Could not apply: ' + detail[:220])
                return
            self.current = target
            self.notify('Wallpaper applied' + (' · Saved to theme' if save else ''))
            # Rebind visible cards so the current marker follows the actual target.
            self.filter_changed()
            if self.source_name == 'Saved':
                self.refresh()

        self.submit(work, ready)

    def notify(self, message: str) -> None:
        self.toast.add_toast(Adw.Toast(title=message, timeout=5))

    def key_pressed(self, controller: Gtk.EventControllerKey, keyval: int, keycode: int, state: Gdk.ModifierType) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and not isinstance(self.get_focus(), Gtk.Button):
            self.apply_selected()
            return True
        if keyval == Gdk.KEY_f and state & Gdk.ModifierType.CONTROL_MASK:
            self.search.grab_focus()
            return True
        return False

    def close_requested(self, *_args: Any) -> bool:
        if self.busy:
            self.notify('Finishing your wallpaper change…')
            return True
        self.closed = True
        self.pool.shutdown(wait=False, cancel_futures=True)
        return False


class Application(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id='io.github.tuxclaw.Backdrop')

    def do_activate(self) -> None:
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        window = self.get_active_window() or Window(self)
        window.present()


def main() -> int:
    if not Gtk.init_check():
        logging.error('Backdrop needs access to a running desktop display.')
        return 1
    return Application().run(None)
