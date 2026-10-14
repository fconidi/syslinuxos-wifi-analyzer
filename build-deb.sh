#!/bin/bash
# Build without root, network access or host installation.
set -euo pipefail
umask 022

PKG_NAME="syslinuxos-wifi-analyzer"
WORKDIR="$(cd "$(dirname "$0")" && pwd)"
PKG_VERSION="$(cat "$WORKDIR/source/VERSION")"
OUTPUT="$WORKDIR/${PKG_NAME}_${PKG_VERSION}_all.deb"

for tool in python3 dpkg-deb desktop-file-validate; do
    command -v "$tool" >/dev/null || { echo "Missing build dependency: $tool" >&2; exit 1; }
done
cd "$WORKDIR"
mkdir -p "$WORKDIR/staging"
PACKAGE_DIR="$(mktemp -d "$WORKDIR/staging/package.XXXXXX")"
chmod 755 "$PACKAGE_DIR"
trap 'rm -rf -- "$PACKAGE_DIR"' EXIT
mkdir -p "$PACKAGE_DIR/DEBIAN" "$PACKAGE_DIR/usr/lib/$PKG_NAME" "$PACKAGE_DIR/usr/share/doc/$PKG_NAME"
for file in "$WORKDIR/source/"*.py "$WORKDIR/source/VERSION" "$WORKDIR/source/beep.wav"; do
    install -m644 "$file" "$PACKAGE_DIR/usr/lib/$PKG_NAME/"
done
install -m755 "$WORKDIR/source/scan-helper" "$PACKAGE_DIR/usr/lib/$PKG_NAME/scan-helper"
install -Dm755 "$WORKDIR/packaging/launcher" "$PACKAGE_DIR/usr/bin/$PKG_NAME"
install -Dm644 "$WORKDIR/packaging/$PKG_NAME.desktop" "$PACKAGE_DIR/usr/share/applications/$PKG_NAME.desktop"
install -Dm644 "$WORKDIR/packaging/$PKG_NAME.menu" "$PACKAGE_DIR/etc/xdg/menus/applications-merged/$PKG_NAME.menu"
echo "/etc/xdg/menus/applications-merged/$PKG_NAME.menu" > "$PACKAGE_DIR/DEBIAN/conffiles"
install -Dm644 "$WORKDIR/packaging/$PKG_NAME.svg" "$PACKAGE_DIR/usr/share/icons/hicolor/scalable/apps/$PKG_NAME.svg"
install -Dm644 "$WORKDIR/packaging/com.syslinuxos.wifi-analyzer.scan.policy" \
    "$PACKAGE_DIR/usr/share/polkit-1/actions/com.syslinuxos.wifi-analyzer.scan.policy"
install -m644 "$WORKDIR/README.md" "$WORKDIR/UPSTREAM.md" "$WORKDIR/packaging/copyright" \
    "$PACKAGE_DIR/usr/share/doc/$PKG_NAME/"
gzip -9 -n -c "$WORKDIR/packaging/changelog" > "$PACKAGE_DIR/usr/share/doc/$PKG_NAME/changelog.gz"
mkdir -p "$PACKAGE_DIR/usr/share/man/man1"
gzip -9 -n -c "$WORKDIR/packaging/$PKG_NAME.1" > "$PACKAGE_DIR/usr/share/man/man1/$PKG_NAME.1.gz"
desktop-file-validate "$PACKAGE_DIR/usr/share/applications/$PKG_NAME.desktop"
python3 - "$PACKAGE_DIR" <<'PY'
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
root = Path(sys.argv[1])
for pattern in ['usr/share/polkit-1/actions/*.policy', 'etc/xdg/menus/applications-merged/*.menu',
                'usr/share/icons/hicolor/scalable/apps/*.svg']:
    for path in root.glob(pattern):
        ET.parse(path)
PY
INSTALLED_SIZE="$(du -sk --exclude=DEBIAN "$PACKAGE_DIR" | cut -f1)"
cat > "$PACKAGE_DIR/DEBIAN/control" <<EOF
Package: $PKG_NAME
Version: $PKG_VERSION
Section: net
Priority: optional
Architecture: all
Maintainer: Franco Conidi <fconidi@gmail.com>
Depends: python3 (>= 3.10), python3-pyqt5 (>= 5.15), python3-pyqt5.qtmultimedia, iw (>= 5.9), pkexec
Recommends: mate-polkit | polkit-1-auth-agent
Conflicts: syslinuxos-wify-analyzer
Replaces: syslinuxos-wify-analyzer
Homepage: https://github.com/fconidi/syslinuxos-wifi-analyzer
Installed-Size: $INSTALLED_SIZE
Description: WiFi signal analyzer and access point locator for SysLinuxOS
 Discover WiFi radios and track a selected BSSID using a signal gauge,
 recent history, peak measurements and adjustable audible feedback.
 Includes a simulated demo and a restricted polkit-authorized scan helper.
EOF
dpkg-deb --root-owner-group --build "$PACKAGE_DIR" "$OUTPUT"
echo "Package ready: $OUTPUT"
