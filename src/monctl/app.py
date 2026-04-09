from __future__ import annotations

import gi
gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")

from gi.repository import Adw, Gio, GLib  # type: ignore

from .config import load_config, DEFAULT_CONFIG_PATH
from .ui import MainWindow


class MonCtlApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.emil.monctl", flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.win = None
        self.cfg = None

        # Actions
        self._add_actions()

    def _add_actions(self):
        # noop
        act_noop = Gio.SimpleAction.new("noop", None)
        self.add_action(act_noop)

        # reload config
        act_reload = Gio.SimpleAction.new("reload", None)
        act_reload.connect("activate", self._on_reload)
        self.add_action(act_reload)

        # apply preset with string parameter via "detailed action"
        act_apply = Gio.SimpleAction.new("apply_preset", GLib.VariantType.new("s"))
        act_apply.connect("activate", self._on_apply_preset)
        self.add_action(act_apply)

    def do_activate(self):
        self._load()
        if not self.win:
            self.win = MainWindow(self, self.cfg)
        self.win.present()

    def _load(self):
        self.cfg = load_config(DEFAULT_CONFIG_PATH)

    def _on_reload(self, *_):
        try:
            self._load()
            if self.win:
                self.win.cfg = self.cfg
                # rebuild preset menu + monitor cards
                self.win._build_preset_menu()
                self.win._render_monitors()
                self.win._notify("Reloaded config")
        except Exception as e:
            if self.win:
                self.win._notify(f"❌ Reload failed: {e}")

    def _on_apply_preset(self, action, param):
        key = param.get_string()
        preset = self.cfg.presets.get(key) if self.cfg else None
        if not preset:
            if self.win:
                self.win._notify(f"❌ Unknown preset '{key}'")
            return
        self.win.apply_preset(preset)


def main():
    app = MonCtlApp()
    app.run()
