#!/usr/bin/env bash

set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/Jeepyto/Togglenix/main"
INSTALL_DIR="$HOME/.local/share/togglenix"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

echo "Installation de Togglenix dans $INSTALL_DIR ..."

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"

if ! command -v nix-build >/dev/null 2>&1; then
  echo
  echo "ATTENTION : nix-build n'est pas trouvé dans ton PATH."
  echo "Cette méthode d'installation nécessite Nix (typiquement NixOS,"
  echo "ou Nix installé sur une autre distro)."
  echo
  exit 1
fi

for file in app.py core.py i18n.py; do
  echo "  - $file"
  curl -fsSL "$REPO_RAW/pkgs/$file" -o "$INSTALL_DIR/$file"
done

curl -fsSL "$REPO_RAW/pkgs/togglenix.svg" -o "$ICON_DIR/togglenix.svg" 2>/dev/null || true

echo "Construction de l'environnement Python+GTK4 (peut prendre une minute la première fois)..."
cat > "$INSTALL_DIR/togglenix-build.nix" << NIXEOF
{ pkgs ? import <nixpkgs> {} }:
let
  pythonWithDeps = pkgs.python3.withPackages (ps: [ ps.pygobject3 ]);
  gtkDeps = with pkgs; [
    gtk4
    libadwaita
    graphene
    pango.out
    gdk-pixbuf
    harfbuzz
    at-spi2-core
    fribidi
    gobject-introspection
  ];
in
pkgs.stdenv.mkDerivation {
  pname = "togglenix";
  version = "0.1.0";
  src = ./.;
  nativeBuildInputs = [ pkgs.makeWrapper pkgs.gobject-introspection ];
  buildInputs = gtkDeps;
  dontBuild = true;
  dontConfigure = true;
  installPhase = ''
    mkdir -p \$out/bin
    makeWrapper \${pythonWithDeps}/bin/python3 \$out/bin/togglenix \\
      --add-flags "$INSTALL_DIR/app.py" \\
      --prefix GI_TYPELIB_PATH : "\${pkgs.lib.makeSearchPath "lib/girepository-1.0" gtkDeps}"
  '';
}
NIXEOF

TOGGLENIX_BUILD_PATH=$(nix-build "$INSTALL_DIR/togglenix-build.nix" --no-out-link)

rm -f "$BIN_DIR/togglenix"
cp "$TOGGLENIX_BUILD_PATH/bin/togglenix" "$BIN_DIR/togglenix"
chmod +x "$BIN_DIR/togglenix"

cat > "$DESKTOP_DIR/togglenix.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Togglenix
Comment=Active ou désactive les modules de ta config NixOS
Exec=$BIN_DIR/togglenix
Icon=togglenix
Terminal=false
Categories=System;Settings;
StartupNotify=true
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

echo
echo "Togglenix est installé."
echo
echo "Lance-le avec : $BIN_DIR/togglenix"
echo
echo "L'environnement a été construit pendant l'installation : les"
echo "lancements de togglenix seront rapides dès maintenant."
echo
echo "L'icône Togglenix devrait aussi apparaître dans le menu"
echo "d'applications (un redémarrage de session peut être nécessaire)."