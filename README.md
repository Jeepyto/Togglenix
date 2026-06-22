<div align="center">
  <img src="togglenix-logo.png" alt="Togglenix logo" width="160">
</div>

English version | **[Version française](README.fr.md)**

# Togglenix

A GTK4/Python app to enable/disable modules in a NixOS config without
hand-editing `.nix` files: a list of modules with switches, an
automatic scanner based on the structure of my own repo
https://github.com/Jeepyto/NixOS-Config that finds your existing
modules — the scan may not work if your structure differs from that
repo, in which case you can also add modules to disable manually — and
an "Apply" button that opens a terminal and triggers a system rebuild.

Togglenix is a **standalone** repository. It's not part of
`NixOS-Config` — it installs alongside it.

## Install

No need to touch your `flake.nix` or `environment.systemPackages`.
This installs Togglenix straight into your `$HOME`:

```bash
curl -fsSL https://raw.githubusercontent.com/Jeepyto/Togglenix/main/install.sh | bash
```
To update later, just re-run the same command.

This builds a self-contained Python/GTK4 environment once (via
`nix-build`), then installs:
- the source in `~/.local/share/togglenix/`
- a `togglenix` launcher script in `~/.local/bin/`
- a menu entry in `~/.local/share/applications/togglenix.desktop`

Once it's done, type `~/.local/bin/togglenix` in a terminal or click its icon in
the application menu. A logout/login (or a `gtk-update-icon-cache`)
may be needed for the icon to show up.

To uninstall:

```bash
rm -rf ~/.local/share/togglenix ~/.local/bin/togglenix ~/.local/share/applications/togglenix.desktop
```

> ⚠️ This method requires Nix to be available (true on NixOS by
> definition, or on any distro with Nix installed). It works as-is on
> [GLF OS](https://framagit.org/gaming-linux-fr/glf-os/glf-os) too.

## If your config lives in `/etc/nixos` (root-owned)

On a typical NixOS install, `/etc/nixos` is owned by `root`, so
Togglenix can read your `.nix` files but can't write to them directly
with your normal user permissions. When that happens, Togglenix
automatically retries the write through `pkexec` — you'll see a system
password prompt the first time you toggle a module, exactly like the
"Apply" button. If your repo lives somewhere in your own `$HOME`
instead, no prompt is needed at all.

## First launch: building your module list

Togglenix starts empty until `~/.config/togglenix/modules.json` exists.
Two ways to fill it in:

**Option A — automatic scan (recommended)**
Open **Preferences** (gear icon, top right) → set `root_path` to your
NixOS config repo → **Scan my repo**. Togglenix walks your repo looking
for `.nix` files, follows import chains, and shows you a flat list of
real modules it found (skipping purely system folders along the way —
see "How the scanner decides what to show" below). Check the ones you
want, click **Import selection**, and they're added to your list —
nothing is modified until you confirm.

**Option B — add modules by hand**
Click the **+** button at the top of the window:
- **Display name**: what you want to see in the list (e.g. "firefox")
- **Category**: used to group the display (e.g. "browsers")
- **default.nix file**: the **full** path, relative to your repo root,
  to the file that contains the relevant `imports = [ ... ];` block —
  note this must be the file itself, not just the folder containing it
- **Imported path**: the exact line as it appears in that `imports`
  block (e.g. `./firefox`)

**If nothing matches and you want to start over**: open Togglenix →
Preferences → **Reset JSON** → confirm. The list is cleared,
`root_path` is kept, and you rebuild manually from scratch.

## A note on module structure on GLF OS (and similar distros)

On some distros (GLF OS for example), packages are usually listed
directly in `environment.systemPackages`, like `pkgs.discord`, rather
than through an `imports = [ ./discord ]` block pointing to a separate
module (which is how the author's own `NixOS-Config` is structured).

Good news: Togglenix already handles both styles with no changes
needed. The "imported path" field doesn't have to start with `./` — it
just needs to match a line in your file exactly. So you can add a
module with **Imported path** set to `pkgs.discord` or `discord`
(instead of `./discord`), and Togglenix will comment/uncomment that
exact line:

```nix
environment.systemPackages = [
  pkgs.vmware-workstation
  pkgs.realvnc-vnc-viewer
  pkgs.discord     # becomes #pkgs.discord when disabled
  pkgs.blender
];
```

## How it works (under the hood)

Togglenix enables or disables a module by commenting/uncommenting its
line inside an `imports = [ ... ];` block (or a `pkgs.xxx` /
`with pkgs; [ ... ]` package list — see the note above).

Example: if `modules/nixos/browsers/default.nix` contains:
```nix
imports = [
  ./firefox
  ./vivaldi
  ./brave
];
```
Togglenix can disable firefox by turning the line into `#./firefox`,
and re-enable it by reversing that.

Togglenix edits the relevant `.nix` file directly, without creating a
backup copy — back up your repo yourself if you want to be able to
roll back a change.

### How the scanner decides what to show

Many NixOS configs nest imports several levels deep purely for
organisation (e.g. `modules` → `nixos` → `environment` → `dev` →
`realvnc`). The scanner is designed to skip all of that and show only
the modules you'd actually want to toggle:

- A `default.nix` is treated as a transparent organisational relay
  whenever **all** of its entries are `./xxx` imports pointing to
  other scanned files — no matter how many levels deep this goes, none
  of these relay folders are shown.
- The module that's actually displayed is the **last** `./xxx` in the
  chain before reaching a file with real content (packages, bare names
  in a `with pkgs; [ ... ]` block, etc.). Its category is the folder of
  the relay right above it — what we call its parent.
- A few folder names are always skipped entirely — `system`,
  `services`, `utilities`, `configuration`, `settings`,
  `game-performance`, `packages` — since they're typically low-level
  system settings rather than toggleable apps. Edit
  `_SCAN_SYSTEM_DIR_NAMES` in `core.py` if your own repo uses different
  names for the same kind of folder.
- `gnome` is a special case: instead of showing a single "gnome" line,
  the scanner lists each package found inside it individually
  (category set to "gnome"), so you can toggle them one by one (an
  exclusive case — the scanner shows the child instead of the parent
  here, by design, to match the author's own repo structure).
- `environment.gnome.excludePackages` is handled with inverted logic:
  a package listed there and *not* commented out is actually
  **uninstalled** (so Togglenix shows it as disabled); toggling it ON
  comments out the line, so it gets reinstalled on the next rebuild.

## Categories, Modules, and Edit tabs

The main window has a view switcher at the top, in this order:

- **Categories** — one switch per category. ON if at least one module
  in the category is active, OFF only if all of them are inactive.
  This switch applies the same state to **every** module in that
  category at once (actually writing to each affected `.nix` file).
- **Modules** — the detailed view, one switch per individual module.
- **Edit** — the same list, but with pencil (edit
  name/category/file/path) and trash (delete this specific module,
  with confirmation) buttons on each row. To wipe the entire list at
  once, use **Reset JSON** in Preferences instead.

## Light / dark theme and language

Togglenix follows the system theme and language by default.

- The sun/moon button in the header bar manually forces light or dark
  mode; this choice is saved and stays active on subsequent launches.
- The FR/EN button does the same for the interface language — it shows
  the language you'd switch *to* (so it reads "EN" while the app is in
  French). Also saved across launches.

## The "Apply" button

It opens a system terminal (tries, in order: `kgx`/GNOME Console,
`gnome-terminal`, `konsole`, `kitty`, `alacritty` — whichever is found
first) and runs a script that:

1. Records the current system generation
2. Runs `pkexec nixos-rebuild switch --flake /etc/nixos`
3. If the rebuild succeeds and a new generation was created, shows the
   closure diff (`nix store diff-closures`) between the old and new
   generation — exactly which packages were added, removed, or changed
4. Waits for you to press **Enter** before closing the window

Togglenix doesn't capture this output in its own interface: follow the
progress and the diff directly in the terminal window that opens, then
click **Reload** (↻ icon) in Togglenix once it's done to refresh the
displayed state. If you use a different flake path or rebuild command,
edit the `rebuild_script` variable in `pkgs/app.py`
(function `_on_apply_clicked`).

## Known limitations (accepted for this version)

- Togglenix only supports one toggle mode: commenting/uncommenting a
  path line. Modules that are only enabled via a `programs.xxx.enable`
  option in their own file aren't covered.
- `pkexec` and the rebuild command must be available in the system
  `PATH` at the moment you click "Apply" (or when writing to a
  root-owned config file).
- The install method (`curl | bash`) requires Nix to be available.
