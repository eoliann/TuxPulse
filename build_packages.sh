#!/usr/bin/env bash
set -euo pipefail

APP_NAME="tuxpulse"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION_FILE="$ROOT_DIR/app/version.py"
DIST_DIR="$ROOT_DIR/dist"
# Identitate instalată separată de TuxPulse2 (pachetul tux-pulse), ca să poată coexista
APP_ID="tuxpulse-classic"
BUILD_DIR="$ROOT_DIR/.pkgbuild"

echo "=== TuxPulse Package Builder ==="

# Citire versiune
if [[ ! -f "$VERSION_FILE" ]]; then
    echo "EROARE: Fișierul $VERSION_FILE nu există!" >&2
    exit 1
fi

VERSION="$(python3 - <<'PY' "$VERSION_FILE"
import re
import sys
from pathlib import Path
content = Path(sys.argv[1]).read_text(encoding='utf-8')
match = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
if not match:
    print("0.0", file=sys.stderr)
    sys.exit(1)
print(match.group(1))
PY
)"

if [[ -z "$VERSION" || "$VERSION" == "0.0" ]]; then
    echo "EROARE: Nu s-a putut citi versiunea din $VERSION_FILE" >&2
    exit 1
fi

echo "Versiune detectată: v${VERSION}"

rm -rf "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$DIST_DIR"

# ================================================
# 1. DEB Package
# ================================================
echo "→ Se construiește pachetul DEB..."

DEB_BUILD="$BUILD_DIR/deb"
mkdir -p "$DEB_BUILD/usr/share/$APP_ID" "$DEB_BUILD/usr/bin" "$DEB_BUILD/usr/share/applications" \
         "$DEB_BUILD/usr/share/icons/hicolor/256x256/apps" "$DEB_BUILD/DEBIAN"

cp -a "$ROOT_DIR/app" "$DEB_BUILD/usr/share/$APP_ID/"
# Nu livrăm fișiere de backup sau bytecode în pachet
find "$DEB_BUILD/usr/share/$APP_ID/app" \( -name "__pycache__" -o -name "*.bk" -o -name "*.bak" -o -name "*.pyc" \) -prune -exec rm -rf {} +

cat > "$DEB_BUILD/usr/bin/$APP_ID" <<LAUNCHER
#!/usr/bin/env bash
exec python3 /usr/share/$APP_ID/app/main.py "\$@"
LAUNCHER
chmod 755 "$DEB_BUILD/usr/bin/$APP_ID"

cat > "$DEB_BUILD/usr/share/applications/$APP_ID.desktop" <<DESKTOP
[Desktop Entry]
Name=TuxPulse Classic
GenericName=System Maintenance
Comment=Linux maintenance toolkit
Exec=$APP_ID
Icon=$APP_ID
StartupWMClass=$APP_ID
Terminal=false
Type=Application
Categories=System;Utility;Settings;
StartupNotify=true
DESKTOP

if [[ -f "$ROOT_DIR/assets/tuxpulse.png" ]]; then
    cp "$ROOT_DIR/assets/tuxpulse.png" "$DEB_BUILD/usr/share/icons/hicolor/256x256/apps/$APP_ID.png"
fi

cat > "$DEB_BUILD/DEBIAN/control" <<EOF
Package: $APP_NAME
Version: $VERSION
Architecture: all
Maintainer: TuxPulse Team
Description: TuxPulse - Linux maintenance toolkit
Depends: python3, python3-pyqt5, python3-psutil, python3-matplotlib
Section: utils
Priority: optional
EOF

cat > "$DEB_BUILD/DEBIAN/postinst" <<EOF
#!/bin/sh
set -e
chmod 755 /usr/bin/$APP_ID
update-desktop-database /usr/share/applications || true
gtk-update-icon-cache /usr/share/icons/hicolor -f -q || true
echo "TuxPulse v${VERSION} installed successfully."
EOF
chmod 755 "$DEB_BUILD/DEBIAN/postinst"

dpkg-deb --build "$DEB_BUILD" "$DIST_DIR/${APP_NAME}_${VERSION}_all.deb"
echo "DEB creat → $DIST_DIR/${APP_NAME}_${VERSION}_all.deb"

# ================================================
# 2. RPM Package (Fedora)
# ================================================
echo "→ Se construiește pachetul RPM..."

if ! command -v rpmbuild >/dev/null 2>&1; then
    echo "EROARE: rpmbuild nu este instalat."
    echo "Instalează-l cu: sudo dnf install rpm-build desktop-file-utils gtk3"
    echo "RPM nu va fi creat."
else
    RPM_BUILD="$BUILD_DIR/rpm"
    mkdir -p "$RPM_BUILD/SPECS" "$RPM_BUILD/SOURCES"

    cp -a "$ROOT_DIR/app" "$RPM_BUILD/SOURCES/"
    find "$RPM_BUILD/SOURCES/app" \( -name "__pycache__" -o -name "*.bk" -o -name "*.bak" -o -name "*.pyc" \) -prune -exec rm -rf {} +

    RPM_ICON_INSTALL=""
    RPM_ICON_FILE=""
    if [[ -f "$ROOT_DIR/assets/tuxpulse.png" ]]; then
        cp "$ROOT_DIR/assets/tuxpulse.png" "$RPM_BUILD/SOURCES/$APP_ID.png"
        RPM_ICON_INSTALL=$'if [ -f %{_sourcedir}/tuxpulse-classic.png ]; then\n    cp %{_sourcedir}/tuxpulse-classic.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/\nfi'
        RPM_ICON_FILE="%{_datadir}/icons/hicolor/256x256/apps/$APP_ID.png"
    fi

    cat > "$RPM_BUILD/SPECS/$APP_NAME.spec" <<SPECFILE
Name:           $APP_NAME
Version:        $VERSION
Release:        1%{?dist}
Summary:        Linux maintenance toolkit
License:        GPL-3.0-or-later
BuildArch:      noarch
Requires:       python3 python3-qt5 python3-psutil python3-matplotlib python3-matplotlib-qt5

%description
TuxPulse - Linux maintenance toolkit.

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/256x256/apps
mkdir -p %{buildroot}%{_datadir}/$APP_ID

cp -a %{_sourcedir}/app %{buildroot}%{_datadir}/$APP_ID/

cat > %{buildroot}%{_bindir}/$APP_ID <<'LAUNCHER_EOF'
#!/usr/bin/env bash
exec python3 %{_datadir}/$APP_ID/app/main.py "\$@"
LAUNCHER_EOF
chmod 755 %{buildroot}%{_bindir}/$APP_ID

cat > %{buildroot}%{_datadir}/applications/$APP_ID.desktop <<'DESKTOP_EOF'
[Desktop Entry]
Name=TuxPulse Classic
GenericName=System Maintenance
Comment=Linux maintenance toolkit
Exec=$APP_ID
Icon=$APP_ID
StartupWMClass=$APP_ID
Terminal=false
Type=Application
Categories=System;Utility;Settings;
StartupNotify=true
DESKTOP_EOF

$RPM_ICON_INSTALL

%post
update-desktop-database %{_datadir}/applications || true
gtk-update-icon-cache %{_datadir}/icons/hicolor -f -q || true

%files
%{_bindir}/$APP_ID
%{_datadir}/applications/$APP_ID.desktop
${RPM_ICON_FILE}
%{_datadir}/$APP_ID

%changelog
* $(LC_ALL=C date +"%a %b %d %Y") TuxPulse Team - $VERSION-1
- Release v$VERSION
SPECFILE

    echo "Se rulează rpmbuild..."
    if ! rpmbuild -bb --define "_topdir $RPM_BUILD" "$RPM_BUILD/SPECS/$APP_NAME.spec"; then
        echo "EROARE: rpmbuild a eșuat. Verifică logul de mai sus."
        exit 1
    fi

    RPM_FILE="$(find "$RPM_BUILD/RPMS" -type f -name "${APP_NAME}-${VERSION}-*.noarch.rpm" | head -n 1 || true)"
    if [[ -n "$RPM_FILE" && -f "$RPM_FILE" ]]; then
        cp "$RPM_FILE" "$DIST_DIR/"
        echo "RPM creat → $DIST_DIR/$(basename "$RPM_FILE")"
    else
        echo "EROARE: Nu s-a găsit RPM-ul generat în $RPM_BUILD/RPMS"
        exit 1
    fi
fi

echo "=== Build finalizat ==="
echo "Conținutul folderului dist/:"
ls -lh "$DIST_DIR"