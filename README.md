# display_orchestrator


copy file:
/etc/udev/rules.d/99-streamdeck.rule


```
sudo dnf install ddcutil python3 python3-pip python3-gobject gtk4 libadwaita
```





# MonCtl Setup and Migration Guide


This guide sets up the full monitor-control stack on a new Linux machine, starting from `git clone`.


It assumes the repository already contains:

- the `monctl` project
- your `config.yml`
- your `.local/bin` helper scripts


It is written for Fedora + GNOME, based on the setup built in this project.


---


## What this setup does


The system gives you:

- individual DDC/CI control of each monitor
- a GTK GUI for switching inputs
- CLI presets via `monctl`
- StreamController integration through shell scripts
- a layout matching your desk:
  - `top` = upper-left monitor
  - `bottom` = lower-left monitor
  - `right` = large monitor on the right


---


## Repository contents expected


Typical structure:


```text
.
├── pyproject.toml
├── src/
│   └── monctl/
│       ├── __init__.py
│       ├── app.py
│       ├── cli.py
│       ├── config.py
│       ├── ddc.py
│       └── ui.py
├── config/
│   └── config.yml
└── local-bin/
    └── monctl-sd/
        └── apply.sh
```


If your repo layout differs, adjust the copy commands below.


---


## 1. Clone the repo


```bash
git clone <your-repo-url> ~/Workspace/Projects/monctl
cd ~/Workspace/Projects/monctl
```


---


## 2. Install system packages


Fedora:


```bash
sudo dnf install -y   ddcutil   python3   python3-pip   python3-gobject   gtk4   libadwaita   libnotify
```


---


## 3. Enable DDC access


Add your user to the `i2c` group:


```bash
sudo usermod -aG i2c $USER
```


Log out and back in before continuing.


---


## 4. Make sure DDC/CI is enabled on all monitors


On each Dell monitor:

- open the monitor OSD
- find **DDC/CI**
- set it to **On**


Without this, `ddcutil` may not work reliably.


---


## 5. Install the Python project for your user


Install from the repo root:


```bash
pip install --user -e .
```


This should create:


```text
~/.local/bin/monctl
~/.local/bin/monctl-gui
```


Verify:


```bash
~/.local/bin/monctl --help
~/.local/bin/monctl-gui
```


---


## 6. Install your config file


Create the config directory:


```bash
mkdir -p ~/.config/monctl
```


Copy the repo config into place:


```bash
cp config/config.yml ~/.config/monctl/config.yml
```


This copied file is only a starting point.

You must still verify bus numbers and input codes on the current machine.


---


## 7. Install Stream Deck helper scripts


Create the target directory:


```bash
mkdir -p ~/.local/bin/monctl-sd
```


Copy scripts from the repo:


```bash
cp -r local-bin/monctl-sd/* ~/.local/bin/monctl-sd/
chmod +x ~/.local/bin/monctl-sd/*
```


If you only use a single script, the important file is:


```text
~/.local/bin/monctl-sd/apply.sh
```


---


## 8. Re-scan monitor buses on this machine


Do not trust old bus numbers.

Re-detect them on the new machine:


```bash
ddcutil detect
```


Create a mapping table:


| Physical monitor | Logical name | Bus |
|---|---|---|
| Upper-left | `top` | ? |
| Lower-left | `bottom` | ? |
| Right large | `right` | ? |


Then verify each bus individually:


```bash
ddcutil -b BUS getvcp 10
ddcutil -b BUS getvcp 60 --terse
```


Replace `BUS` with the detected bus number.


---


## 9. Re-scan input codes for each monitor


This is required because input codes can differ per monitor.


For each monitor bus:


```bash
ddcutil -b BUS capabilities
ddcutil -b BUS getvcp 60 --terse
```


Now manually switch the monitor to each connected source and record the code.


For each monitor, test these sources if connected:

- `Desktop`
- `Laptop`
- `Orchestrator`
- `Switch`


Build a table like this:


| Monitor | Desktop | Laptop | Orchestrator | Switch |
|---|---|---|---|---|
| top | `0x??` | `0x??` | `0x??` | `0x??` |
| bottom | `0x??` | `0x??` | `0x??` | maybe none |
| right | `0x??` | `0x??` | `0x??` | maybe none |


---


## 10. Update `~/.config/monctl/config.yml`


Edit the file and update:

- `bus` for each monitor
- input codes for each source
- presets as needed


Typical shape:


```yaml
monitors:
  top:
    name: Top Dell
    bus: 9
    inputs:
      Desktop: "0x??"
      Laptop: "0x??"
      Orchestrator: "0x??"
      Switch: "0x??"

  bottom:
    name: Bottom Dell
    bus: 6
    inputs:
      Desktop: "0x??"
      Laptop: "0x??"
      Orchestrator: "0x??"

  right:
    name: Right Dell
    bus: 7
    inputs:
      Desktop: "0x??"
      Laptop: "0x??"
      Orchestrator: "0x??"

presets:
  orchestrator_all:
    name: Orchestrator on all screens
    set:
      top: Orchestrator
      bottom: Orchestrator
      right: Orchestrator

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

  desktop_main:
    name: Desktop main
    set:
      top: Laptop
      bottom: Desktop
      right: Desktop

  laptop_main:
    name: Laptop main
    set:
      top: Desktop
      bottom: Laptop
      right: Laptop

  switch_top:
    name: Switch top
    set:
      top: Switch
      bottom: Orchestrator
      right: Orchestrator
```


Adjust values and preset names to match your real setup.


---


## 11. Verify individual monitor control


Before using presets, prove that each monitor can be controlled independently.


Examples:


```bash
monctl set top Orchestrator
monctl set bottom Desktop
monctl set right Laptop
```


Acceptance criteria:

- only the intended monitor changes
- no two monitors are swapped
- all input labels point to the correct real source


If a command affects the wrong monitor, fix the bus mapping first.


---


## 12. Test mixed layouts


Validate that the setup can control all monitors independently.


Examples to test:

- top → `Switch`, bottom → `Desktop`, right → `Orchestrator`
- top → `Laptop`, bottom → `Orchestrator`, right → `Desktop`
- top → `Desktop`, bottom → `Laptop`, right → `Laptop`


If these all work, your control plane is correct.


---


## 13. Launch the GUI


Run:


```bash
monctl-gui
```


Verify:

- the physical layout is correct
- the monitor cards are shown as `top`, `bottom`, `right`
- the active input subtitle updates
- clicking a button changes only the selected monitor


---


## 14. Optional: create a desktop launcher


Create:


```text
~/.local/share/applications/monctl.desktop
```


With this content:


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


## 15. Set up StreamController


Make sure your Stream Deck is detected on this machine and that StreamController can run commands.


Your buttons should call:


```bash
/home/emil/.local/bin/monctl-sd/apply.sh orchestrator_all
/home/emil/.local/bin/monctl-sd/apply.sh desktop_all
/home/emil/.local/bin/monctl-sd/apply.sh laptop_all
/home/emil/.local/bin/monctl-sd/apply.sh desktop_main
/home/emil/.local/bin/monctl-sd/apply.sh laptop_main
/home/emil/.local/bin/monctl-sd/apply.sh switch_top
```


If your preset names differ, update the command arguments.


---


## 16. Optional: Stream Deck permissions


If the Stream Deck is not detected on the new machine, recreate the udev rule:


```text
/etc/udev/rules.d/99-streamdeck.rules
```


Typical example:


```udev
ACTION=="add|change", SUBSYSTEM=="hidraw", ENV{ID_VENDOR_ID}=="0fd9", ENV{ID_MODEL_ID}=="006d", MODE="0666"
```


Then reload rules and replug the device:


```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```


If StreamController is installed as Flatpak, you may also need:


```bash
flatpak override --user --device=all --filesystem=home com.github.StreamController.StreamController
```


---


## 17. Final acceptance checklist


You are done when all of these are true:


### Monitor discovery

- `ddcutil detect` finds all three monitors
- each monitor has the correct bus number


### Input mapping

- each source has a known input code on each monitor
- `config.yml` contains correct values


### App functionality

- `monctl set ...` works
- `monctl preset ...` works
- `monctl-gui` works and shows correct active inputs


### Independent control

- `top` changes independently
- `bottom` changes independently
- `right` changes independently
- mixed layouts work correctly


### Stream Deck integration

- StreamController can run `apply.sh`
- each button triggers the correct preset


---


## 18. Recommended first-pass workflow


If you want the shortest safe path, do these steps first:


1. clone the repo
2. install packages
3. install `monctl`
4. copy `config.yml`
5. run `ddcutil detect`
6. fix bus numbers
7. re-scan input codes
8. update `config.yml`
9. verify `monctl set ...`
10. test `monctl-gui`
11. reconnect StreamController


Once those are working, the rest is just polish.