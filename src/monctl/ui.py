from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from gi.repository import Adw, Gtk, GLib  # type: ignore

from .config import AppConfig, Monitor, Preset
from . import ddc


@dataclass
class Action:
    title: str
    run: Callable[[], None]


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, cfg: AppConfig):
        super().__init__(application=app)
        self.cfg = cfg
        self.set_title("MonCtl")
        self.set_default_size(1200, 420)
        self._monitor_buttons: dict[str, dict[str, Gtk.Button]] = {}
        self._active_labels: dict[str, str | None] = {}


        # Toast overlay (for notifications)
        self.toast = Adw.ToastOverlay()

        # Header bar
        header = Adw.HeaderBar()

        # Presets menu button
        self.preset_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
        self.preset_btn.set_tooltip_text("Presets")
        header.pack_start(self.preset_btn)

        # Refresh config button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Reload config")
        refresh_btn.connect("clicked", self._on_reload_clicked)

        refresh_active_inputs_btn = Gtk.Button(icon_name="open-menu-symbolic")
        refresh_active_inputs_btn.set_tooltip_text("Refresh inputs")
        refresh_active_inputs_btn.connect("clicked", self.refresh_active_inputs)
        header.pack_end(refresh_btn)

        # Toolbar view: proper Adwaita layout container
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)

        # Main content: scroller -> flowbox grid
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_hexpand(True)
        self.scroller.set_vexpand(True)

        self.layout_grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        self.layout_grid.set_margin_top(12)
        self.layout_grid.set_margin_bottom(12)
        self.layout_grid.set_margin_start(12)
        self.layout_grid.set_margin_end(12)

        self.scroller.set_child(self.layout_grid)

        self._active_labels_ui: dict[str, Adw.ActionRow] = {}

        # Put scroller into toolbar view, then into toast overlay, then into window
        toolbar_view.set_content(self.scroller)
        self.toast.set_child(toolbar_view)
        self.set_content(self.toast)

        # Build menus + render
        self._build_preset_menu()
        self._render_monitors()

    def _notify(self, text: str):
        self.toast.add_toast(Adw.Toast.new(text))

    def _run_in_thread(self, fn, done_cb):
        """
        Run fn() in a thread, then call done_cb(result) on GTK main loop.
        """
        def _worker():
            res = fn()
            GLib.idle_add(done_cb, res, priority=GLib.PRIORITY_DEFAULT)
            return False

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def _build_preset_menu(self):
        from gi.repository import Gio  # type: ignore

        menu = Gio.Menu()

        if not self.cfg.presets:
            menu.append("No presets", "app.noop")
        else:
            for key, preset in self.cfg.presets.items():
                # This calls the action 'apply_preset' with a string parameter.
                menu.append(preset.name, f"app.apply_preset('{key}')")

        self.preset_btn.set_menu_model(menu)

    def _on_reload_clicked(self, *_):
        # reload handled by app (simpler); just emit action
        self.get_application().activate_action("reload", None)

    def _render_monitors(self):
        # clear grid
        self._monitor_buttons = {}
        child = self.layout_grid.get_first_child()
        self._active_labels_ui = {}

        while child:
            self.layout_grid.remove(child)
            child = self.layout_grid.get_first_child()

        # Left stack: top + bottom
        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        if "top" in self.cfg.monitors:
            left_col.append(self._monitor_card(self.cfg.monitors["top"]))
        if "bottom" in self.cfg.monitors:
            left_col.append(self._monitor_card(self.cfg.monitors["bottom"]))

        # Right: 42"
        right_widget = self._monitor_card(self.cfg.monitors["right"]) if "right" in self.cfg.monitors else Gtk.Box()

        self.layout_grid.attach(left_col, 0, 0, 1, 1)
        self.layout_grid.attach(right_widget, 1, 0, 1, 1)
        self.refresh_active_inputs()

    def _monitor_card(self, mon: Monitor) -> Gtk.Widget:
        card = Adw.Clamp()
        card.set_maximum_size(620)
        self._monitor_buttons.setdefault(mon.key, {})

        frame = Adw.PreferencesGroup()
        frame.set_title(mon.name)
        frame.set_description("")  # we'll show a custom "Active" line instead

        active_lbl = Gtk.Label(label="Active: –")
        active_lbl.set_xalign(0)
        active_lbl.add_css_class("dim-label")  # subtle GNOME style
        self._active_labels_ui[mon.key] = active_lbl

        # Put label under title using an ActionRow (nice spacing)
        status_row = Adw.ActionRow()
        status_row.set_title("Status")
        status_row.set_subtitle("Active: –")
        # Alternatively: attach the Gtk.Label as a suffix; but subtitle is simplest
        frame.add(status_row)

        # Store row so we can update subtitle later
        # We'll store the row instead of label:
        self._active_labels_ui[mon.key] = status_row

        # Buttons row
        row = Adw.ActionRow()
        row.set_title("Inputs")

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_box.set_halign(Gtk.Align.END)
        group = None  # radio group per monitor
        for label, code in mon.inputs.items():
            btn = Gtk.ToggleButton(label=label)

            # Make them behave like radio buttons (one active at a time)
            if group is not None:
                btn.set_group(group)
            else:
                group = btn

            # IMPORTANT: don’t let toggling itself trigger switching
            # (we’ll switch only on click, and we’ll set_active() from refresh)
            btn.connect(
                "clicked",
                lambda _b, m=mon, l=label, c=code: self._switch_one(m, l, c)
            )

            self._monitor_buttons.setdefault(mon.key, {})
            self._monitor_buttons[mon.key][label] = btn
            btn_box.append(btn)

        row.add_suffix(btn_box)
        frame.add(row)

        card.set_child(frame)
        return card

    def _switch_one(self, mon: Monitor, label: str, code: str):
        self._notify(f"{mon.name} → {label}")

        last = self._active_labels.get(mon.key)

        buttons = self._monitor_buttons.get(mon.key, {})
        for lbl, btn in buttons.items():
            btn.set_active(lbl == last)

        def work():
            return ddc.set_input(mon.bus, code, retries=3)

        def done(res: ddc.DdcResult):
            if res.ok:
                self._notify(f"{mon.name} set to {label}")
            else:
                self._notify(f"{mon.name} failed: {res.message}")

            self.refresh_active_inputs()
            return False

        self._run_in_thread(work, done)

    def apply_preset(self, preset: Preset):
        """
        Apply preset: for each monitor_key in preset.set, switch to input_label.
        """
        self._notify(f"Applying preset: {preset.name}")

        # Build a list of operations in order
        ops = []
        for mon_key, input_label in preset.set.items():
            mon = self.cfg.monitors.get(mon_key)
            if not mon:
                ops.append((False, f"Unknown monitor '{mon_key}'"))
                continue
            code = mon.inputs.get(input_label)
            if not code:
                ops.append((False, f"{mon.name}: unknown input '{input_label}'"))
                continue
            ops.append((mon, input_label, code))

        def work():
            results = []
            for item in ops:
                if item[0] is False:
                    results.append(item)
                    continue
                mon, label, code = item
                results.append((mon, label, ddc.set_input(mon.bus, code, retries=3)))
            return results

        def done(results):
            failures = 0
            for item in results:
                if item[0] is False:
                    failures += 1
                    self._notify(f"❌ {item[1]}")
                    continue
                mon, label, res = item
                if res.ok:
                    self._notify(f"✅ {mon.name} → {label}")
                else:
                    failures += 1
                    self._notify(f"❌ {mon.name}: {res.message}")
            if failures == 0:
                self._notify(f"Done: {preset.name}")
            else:
                self._notify(f"Done with {failures} issue(s)")
            return False

        self._run_in_thread(work, done)

    def refresh_active_inputs(self):
        # Query each monitor async and update button styles
        for mon in self.cfg.monitors.values():
            def work(m=mon):
                return (m, ddc.get_input(m.bus))

            def done(result):

                mon_obj, res = result
                if not res.ok:
                    self._notify(f"❌ {mon_obj.name}: {res.message}")
                    return False

                active_code = res.message  # the hex code
                # invert inputs: code -> label
                code_to_label = {v.lower(): k for k, v in mon_obj.inputs.items()}
                active_label = code_to_label.get(active_code)
                self._active_labels[mon_obj.key] = active_label

                status_row = self._active_labels_ui.get(mon_obj.key)
                if status_row:
                    status_row.set_subtitle(f"Active: {active_label or 'Unknown'}")

                # print(mon_obj.key, "active_code=", active_code, "active_label=", active_label)

                # clear highlighting
                buttons = self._monitor_buttons.get(mon_obj.key, {})

                for lbl, btn in buttons.items():
                    btn.set_active(lbl == active_label)
                    # btn.set_sensitive(True)

                if not active_label:
                    for btn in buttons.values():
                        btn.set_active(False)
                    return False

                return False

            self._run_in_thread(work, done)


# Tiny helper so we don’t need a .ui file yet
class GioMenu:
    def __init__(self):
        from gi.repository import Gio  # type: ignore
        self.Gio = Gio
        self.menu = Gio.Menu()

    def append(self, label: str, detailed_action: str):
        self.menu.append(label, detailed_action)

    def get_menu_model(self):
        return self.menu

    def __getattr__(self, item):
        return getattr(self.menu, item)
