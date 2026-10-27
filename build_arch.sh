#!/usr/bin/env bash
set -euo pipefail

APP_NAME="tuxpulse"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="$ROOT_DIR/app/version.py"
DIST_DIR="$ROOT_DIR/dist"
INSTALL_AFTER=false

usage() {
  cat <<'USAGE'
Usage:
  ./build_arch.sh           Build the Arch package into dist/
  ./build_arch.sh --install Build the package and install it on Arch/CachyOS
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --install)
      INSTALL_AFTER=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$VERSION_FILE" ]]; then
  echo "ERROR: $VERSION_FILE not found" >&2
  exit 1
fi

VERSION="$(python3 - <<'PY' "$VERSION_FILE"
import re
import sys
from pathlib import Path
content = Path(sys.argv[1]).read_text(encoding='utf-8')
match = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
if not match:
    raise SystemExit('Could not read APP_VERSION from app/version.py')
print(match.group(1))
PY
)"

mkdir -p "$DIST_DIR"
if [[ ! -w "$DIST_DIR" ]]; then
  echo 'ERROR: dist is not writable. Fix ownership first, for example:' >&2
  echo '  sudo chown -R "$USER":"$USER" dist' >&2
  exit 1
fi

WORKSPACE="$(mktemp -d /tmp/tuxpulse-archbuild.XXXXXX)"
trap 'rm -rf "$WORKSPACE"' EXIT
SRCROOT="$WORKSPACE/src/${APP_NAME}-${VERSION}"
mkdir -p "$SRCROOT"

for item in app packaging assets LICENSE LICENSE.md README.md; do
  if [[ -e "$ROOT_DIR/$item" ]]; then
    cp -a "$ROOT_DIR/$item" "$SRCROOT/"
  fi
done
find "$SRCROOT/app" \( -name "__pycache__" -o -name "*.bk" -o -name "*.bak" -o -name "*.pyc" \) -prune -exec rm -rf {} +

cat > "$WORKSPACE/PKGBUILD" <<PKGEOF
pkgname=${APP_NAME}
pkgver=${VERSION}
pkgrel=1
pkgdesc="Multi-distro Linux maintenance and installer toolkit"
arch=('any')
url="https://github.com/eoliann/TuxPulse"
license=('MIT')
depends=('python' 'python-pyqt5' 'python-psutil' 'python-matplotlib' 'polkit')
optdepends=('flatpak: Flatpak app installation support')
install='tuxpulse.install'
source=()
sha256sums=()

package() {
    cd "\$srcdir/${APP_NAME}-${VERSION}"

    install -dm755 "\$pkgdir/usr/share/tuxpulse"
    cp -a app "\$pkgdir/usr/share/tuxpulse/"

    if [[ -f packaging/deb/usr/bin/tuxpulse ]]; then
        install -Dm755 packaging/deb/usr/bin/tuxpulse "\$pkgdir/usr/bin/tuxpulse"
    else
        install -Dm755 /dev/stdin "\$pkgdir/usr/bin/tuxpulse" <<'LAUNCHER'
#!/usr/bin/env bash
export PYTHONPATH="/usr/share/tuxpulse/app"
exec /usr/bin/python /usr/share/tuxpulse/app/main.py "\$@"
LAUNCHER
    fi

    if [[ -f packaging/deb/usr/share/applications/tuxpulse.desktop ]]; then
        install -Dm644 packaging/deb/usr/share/applications/tuxpulse.desktop \
            "\$pkgdir/usr/share/applications/tuxpulse.desktop"
    else
        install -Dm644 /dev/stdin "\$pkgdir/usr/share/applications/tuxpulse.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=TuxPulse
Comment=TuxPulse System Toolkit
Exec=/usr/bin/tuxpulse
Icon=tuxpulse
Terminal=false
Categories=Utility;System;
StartupNotify=true
StartupWMClass=tuxpulse
DESKTOP
    fi

    if [[ -f assets/tuxpulse.png ]]; then
        install -Dm644 assets/tuxpulse.png \
            "\$pkgdir/usr/share/icons/hicolor/256x256/apps/tuxpulse.png"
    elif [[ -f packaging/deb/usr/share/icons/hicolor/256x256/apps/tuxpulse.png ]]; then
        install -Dm644 packaging/deb/usr/share/icons/hicolor/256x256/apps/tuxpulse.png \
            "\$pkgdir/usr/share/icons/hicolor/256x256/apps/tuxpulse.png"
    fi
}
PKGEOF

cat > "$WORKSPACE/tuxpulse.install" <<'INSTEOF'
post_install() {
  cat <<'MSG'
TuxPulse was installed successfully.

Run it with:
  tuxpulse
MSG
}

post_upgrade() {
  post_install
}
INSTEOF

echo "Project root: $ROOT_DIR"
echo "Arch packaging source: $ROOT_DIR/packaging/arch"
echo "Workspace: $WORKSPACE"
echo "Output: $DIST_DIR"
echo "Version: $VERSION"

build_native() {
  echo "Building Arch package natively with makepkg..."
  (
    cd "$WORKSPACE"
    makepkg -fs --noconfirm
  )
  find "$WORKSPACE" -maxdepth 1 -type f -name "${APP_NAME}-${VERSION}-*.pkg.tar.zst" -exec cp -f {} "$DIST_DIR/" \;
}

build_in_podman() {
  echo "Building Arch package from packaging/arch via podman..."
  podman run --rm \
    -v "$WORKSPACE:/work:ro,z" \
    -v "$DIST_DIR:/out:rw,z" \
    docker.io/library/archlinux:latest \
    bash -lc '
      set -euo pipefail
      pacman -Syu --noconfirm --needed base-devel >/dev/null
      rm -rf /tmp/build
      mkdir -p /tmp/build
      cp -a /work/. /tmp/build/
      useradd -m builder
      chown -R builder:builder /tmp/build
      su builder -c "cd /tmp/build && makepkg -fs --noconfirm"
      cp -f /tmp/build/'"${APP_NAME}-${VERSION}"'-*.pkg.tar.zst /out/
    '
}

if command -v makepkg >/dev/null 2>&1 && command -v pacman >/dev/null 2>&1; then
  build_native
elif command -v podman >/dev/null 2>&1; then
  build_in_podman
else
  echo "ERROR: Neither native Arch build tools nor podman are available." >&2
  echo "On CachyOS/Arch install base-devel; on Mint/Ubuntu install podman." >&2
  exit 1
fi

PACKAGE_FILE="$(find "$DIST_DIR" -maxdepth 1 -type f -name "${APP_NAME}-${VERSION}-*.pkg.tar.zst" | sort | tail -n 1)"

if [[ -z "$PACKAGE_FILE" ]]; then
  echo "ERROR: Package was not created in $DIST_DIR" >&2
  exit 1
fi

echo
echo "Package created:"
echo "  $PACKAGE_FILE"

if [[ "$INSTALL_AFTER" == true ]]; then
  if command -v pacman >/dev/null 2>&1; then
    echo
    echo "Installing package with pacman..."
    sudo pacman -U --noconfirm "$PACKAGE_FILE"
  else
    echo
    echo "Build finished, but auto-install is available only on Arch/CachyOS systems with pacman."
  fi
fi