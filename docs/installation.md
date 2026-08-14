# Installation

Fan Control UI requires Linux, Python 3.10 or newer, and at least one
fan-related `fanN_*` or `pwmN*` endpoint under `/sys/class/hwmon`.

## Arch Linux (AUR)

Install [`fancontrol-ui` from the AUR][aur-package] with an AUR helper:

```bash
paru -S fancontrol-ui
```

You can also build the package manually:

```bash
git clone https://aur.archlinux.org/fancontrol-ui.git
cd fancontrol-ui
makepkg -si
```

Review AUR build files before running `makepkg`. The package installs the
application, desktop entry, icon, license, and the included udev rules.

## From source

Create an isolated environment and install the checkout:

```bash
git clone https://github.com/rockybranches/fancontrol-ui.git
cd fancontrol-ui
python -m venv .venv
. .venv/bin/activate
python -m pip install .
fancontrol-ui
```

## Hardware permissions

Hardware monitoring files are commonly writable only by root. The repository's
`60-fan-control.rules` provides udev rules for supported access patterns.
Prefer narrowly scoped udev rules or a system service over running the entire
graphical application as root.

After changing udev rules, reload them and reconnect or reprobe the affected
device:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

[aur-package]: https://aur.archlinux.org/packages/fancontrol-ui
