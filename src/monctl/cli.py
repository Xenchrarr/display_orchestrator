from __future__ import annotations

import argparse
import sys

from .config import load_config, DEFAULT_CONFIG_PATH
from .ddc import set_input


def main():
    parser = argparse.ArgumentParser(prog="monctl")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_preset = sub.add_parser("preset", help="Apply a preset from config")
    p_preset.add_argument("name", help="Preset key")

    p_set = sub.add_parser("set", help="Set one monitor to an input label")
    p_set.add_argument("monitor", help="Monitor key")
    p_set.add_argument("input", help="Input label as defined in config")

    args = parser.parse_args()

    cfg = load_config(DEFAULT_CONFIG_PATH)

    if args.cmd == "preset":
        preset = cfg.presets.get(args.name)
        if not preset:
            print(f"Unknown preset: {args.name}", file=sys.stderr)
            return 2
        for mon_key, input_label in preset.set.items():
            mon = cfg.monitors.get(mon_key)
            if not mon:
                print(f"Unknown monitor '{mon_key}'", file=sys.stderr)
                continue
            code = mon.inputs.get(input_label)
            if not code:
                print(f"{mon.name}: unknown input '{input_label}'", file=sys.stderr)
                continue
            res = set_input(mon.bus, code, retries=3)
            print(("OK  " if res.ok else "FAIL"), mon.name, "->", input_label, "-", res.message)
        return 0

    if args.cmd == "set":
        mon = cfg.monitors.get(args.monitor)
        if not mon:
            print(f"Unknown monitor: {args.monitor}", file=sys.stderr)
            return 2
        code = mon.inputs.get(args.input)
        if not code:
            print(f"Unknown input '{args.input}' for monitor '{args.monitor}'", file=sys.stderr)
            return 2
        res = set_input(mon.bus, code, retries=3)
        print(res.message)
        return 0 if res.ok else 1
