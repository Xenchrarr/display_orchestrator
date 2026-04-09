# MonCtl

Monitor input switcher for Linux using DDC/CI.
Controls multiple monitors via `ddcutil`, with a CLI, a GTK4/libadwaita GUI, and optional Stream Deck integration.

**Default physical layout:**

| Name | Position |
|------|----------|
| `top` | Upper-left monitor |
| `bottom` | Lower-left monitor |
| `right` | Large right monitor |

---

## Repository structure

```
.
├── pyproject.toml
├── config.yml                  ← example config (copy to ~/.config/monctl/)
├── 99-streamdeck.rules         ← udev rule for Stream Deck
├── bin/
│   ├── monctl                  ← CLI entry point (installed by pip)
│   ├── monctl-gui              ← GUI entry point (installed by pip)
│   └── monctl-sd/              ← Stream Deck helper scripts
│       ├── apply.sh            ← apply a named preset
│       ├── set.sh              ← set one monitor to one input
│       ├── desktop-all.sh
│       ├── laptop-all.sh
│       └── ...
└── src/
    └── monctl/
        ├── cli.py
        ├── app.py
        ├── ui.py
        ├── config.py
        └── ddc.py
```

---

## 1. Install system packages

Fedora / RHEL:

```bash
sudo dnf install -y ddcutil python3 python3-pip python3-gobject gtk4 libadwaita libnotify
```

---

## 2. Grant DDC/CI access

Add your user to the `i2c` group so `ddcutil` can talk to monitors without root:

```bash
sudo usermod -aG i2c $USER
```

Log out and back in before continuing.

Also make sure **DDC/CI is enabled** in the OSD of every monitor (usually under Personalize or Input settings).

---

## 3. Install the Python package

From the repo root:

```bash
pip install --user -e .
```

This installs two entry points into `~/.local/bin/`:

```
~/.local/bin/monctl
~/.local/bin/monctl-gui
```

Make sure `~/.local/bin` is on your `$PATH`. Verify:

```bash
monctl --help
```

---

## 4. Install the config file

```bash
mkdir -p ~/.config/monctl
cp config.yml ~/.config/monctl/config.yml
```

The config at `~/.config/monctl/config.yml` is the live config that MonCtl reads at runtime. The file in the repo is only a reference — you must update it with the correct bus numbers and input codes for your machine (see steps 5–7).

---

## 5. Detect monitor bus numbers

Run:

```bash
ddcutil detect
```

Each monitor will be listed with an I2C bus number. Map them to your physical layout:

| Physical monitor | Config key | Bus |
|------------------|------------|-----|
| Upper-left       | `top`      | ?   |
| Lower-left       | `bottom`   | ?   |
| Right            | `right`    | ?   |

Verify a bus responds:

```bash
ddcutil -b BUS getvcp 10        # brightness — should return a value
ddcutil -b BUS getvcp 60 --terse  # current input code
```

---

## 6. Find input codes for each monitor

Each physical input port has a numeric code. Codes differ between monitor models.

For each monitor bus, list supported inputs:

```bash
ddcutil -b BUS capabilities | grep -A5 "Feature: 60"
```

Then manually switch the monitor to each source you use and read back the active code:

```bash
ddcutil -b BUS getvcp 60 --terse
```

Build a table and fill in `~/.config/monctl/config.yml`:

| Monitor  | Desktop | Laptop | Switch | Orchestrator |
|----------|---------|--------|--------|--------------|
| `top`    | `0x??`  | `0x??` | `0x??` | `0x??`       |
| `bottom` | `0x??`  | `0x??` | —      | `0x??`       |
| `right`  | `0x??`  | `0x??` | —      | `0x??`       |

---

## 7. Update config.yml

Edit `~/.config/monctl/config.yml`. The format is:

```yaml
monitors:
  top:
    name: Top Dell
    bus: 9
    inputs:
      Desktop: "0x10"
      Laptop: "0x11"
      Orchestrator: "0x0f"
      Switch: "0x13"

  bottom:
    name: Bottom Dell
    bus: 6
    inputs:
      Desktop: "0x12"
      Laptop: "0x11"

  right:
    name: Right Dell
    bus: 7
    inputs:
      Desktop: "0x0f"
      Laptop: "0x12"
      Switch: "0x13"

presets:
  desktop_all:
    name: Desktop on all screens
    set:
      top: Desktop
      bottom: Desktop
      right: Desktop

  laptop_all:
    name: Laptop on all screens
    set:
      top: Laptop
      bottom: Laptop
      right: Laptop

  split_d2_l1:
    name: Desktop 2 + Laptop 1
    set:
      top: Laptop
      bottom: Desktop
      right: Desktop

  split_d1_l2:
    name: Desktop 1 + Laptop 2
    set:
      top: Desktop
      bottom: Laptop
      right: Laptop

  orchestrator_top:
    name: Orchestrator on top
    set:
      top: Orchestrator
```

Add or remove presets and inputs to match your real sources.

---

## 8. Verify CLI control

Test each monitor individually:

```bash
monctl set top Desktop
monctl set bottom Laptop
monctl set right Desktop
```

Only the named monitor should change. If the wrong monitor changes, fix the bus mapping in config.

Test a preset:

```bash
monctl preset desktop_all
monctl preset laptop_all
```

---

## 9. Launch the GUI

```bash
monctl-gui
```

The window shows a card for each monitor with buttons for each configured input. Clicking a button sends the DDC command immediately. The active input subtitle updates after the switch.

The **Presets** menu in the header bar applies full layouts in one click. The reload button re-reads `~/.config/monctl/config.yml` without restarting.

---

## 10. Optional: desktop launcher

Create `~/.local/share/applications/monctl.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=MonCtl
Exec=monctl-gui
Icon=video-display-symbolic
Terminal=false
Categories=Utility;
```

---

## 11. Stream Deck integration

### Install helper scripts

```bash
mkdir -p ~/.local/bin/monctl-sd
cp bin/monctl-sd/* ~/.local/bin/monctl-sd/
chmod +x ~/.local/bin/monctl-sd/*
```

### Wire up buttons in StreamController

Each button should run a shell command. Use the wrapper scripts:

| Script | What it does |
|--------|--------------|
| `apply.sh <preset>` | Apply a named preset from config |
| `set.sh <monitor> <input>` | Set one monitor to one input |
| `desktop-all.sh` | Shortcut for `monctl preset desktop_all` |
| `laptop-all.sh` | Shortcut for `monctl preset laptop_all` |

Example button command:

```bash
/home/YOUR_USER/.local/bin/monctl-sd/apply.sh desktop_all
```

### Stream Deck udev rule

If the Stream Deck is not detected, install the udev rule from the repo:

```bash
sudo cp 99-streamdeck.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then replug the device.

If running StreamController as a Flatpak:

```bash
flatpak override --user --device=all --filesystem=home com.github.StreamController.StreamController
```

---

## CLI reference

```
monctl set <monitor> <input>     Set one monitor to a named input
monctl preset <preset>           Apply a full preset from config
```

Both commands exit `0` on success, non-zero on failure. Output is one line per monitor showing `OK` or `FAIL`.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ddcutil detect` finds no monitors | Check `i2c` group membership; re-login |
| Wrong monitor changes | Bus numbers are swapped — re-detect and fix config |
| `ddcutil` times out on one monitor | DDC/CI is disabled in that monitor's OSD |
| `monctl: command not found` | `~/.local/bin` not on `$PATH`; add it to `~/.bashrc` or `~/.profile` |
| GUI shows no monitors | Config file missing or empty — check `~/.config/monctl/config.yml` |
| Stream Deck not detected | Install udev rule; replug device |
