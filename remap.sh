#!/bin/bash
#
# Logitech G300s Button Remapper
#
# Remaps G300s extra buttons to OS-specific gesture shortcuts.
# Run this script ON a Linux machine with the G300s plugged in.
# Auto-installs dependencies (libusb, ratslap) if missing.
#
# Usage:
#   ./remap.sh mac              # macOS gesture shortcuts
#   ./remap.sh windows          # Windows gesture shortcuts
#   ./remap.sh show             # Show current config
#   ./remap.sh reset            # Reset to factory
#
# Physical button layout:
#   G5 (upper-left)    G7 (upper-right)
#   G4 (lower-left)    G6 (lower-right)
#              G9 (bottom-center)
#   G8 = ModeSwitch (profile cycle, not remapped)

set -euo pipefail

RATSLAP_DIR="/tmp/ratslap"
PROFILES="F3 F4 F5"

usage() {
    cat <<'EOF'
Usage: ./remap.sh <mac|windows|show|reset>

Profiles:
  mac      - macOS gestures (Mission Control, Spaces, Exposé, Back)
  windows  - Windows gestures (Task View, Virtual Desktops, Back)
  show     - Show current button assignments
  reset    - Reset to factory defaults

Run on a Linux machine with G300s plugged in via USB.
Dependencies are installed automatically.
EOF
    exit 1
}

# --- Dependency setup ---

install_deps() {
    echo "[1/3] Checking dependencies..."

    # libusb dev headers
    if ! dpkg -s libusb-1.0-0-dev &>/dev/null; then
        echo "  Installing libusb-1.0-0-dev..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq libusb-1.0-0-dev
    else
        echo "  libusb-1.0-0-dev OK"
    fi

    # build tools
    if ! command -v gcc &>/dev/null || ! command -v make &>/dev/null; then
        echo "  Installing build-essential..."
        sudo apt-get install -y -qq build-essential
    else
        echo "  build tools OK"
    fi

    # git
    if ! command -v git &>/dev/null; then
        echo "  Installing git..."
        sudo apt-get install -y -qq git
    else
        echo "  git OK"
    fi
}

build_ratslap() {
    echo "[2/3] Checking ratslap..."

    if [[ -x "$RATSLAP_DIR/ratslap" ]]; then
        echo "  ratslap already built"
        return
    fi

    echo "  Cloning and building ratslap..."
    rm -rf "$RATSLAP_DIR"
    git clone --quiet https://github.com/krayon/ratslap.git "$RATSLAP_DIR"
    cd "$RATSLAP_DIR" && make --quiet
    echo "  ratslap built OK"
}

setup_udev() {
    echo "[3/3] Checking USB permissions..."

    local rule='SUBSYSTEM=="usb", ATTR{idVendor}=="046d", ATTR{idProduct}=="c246", MODE="0666"'
    local rulefile="/etc/udev/rules.d/99-g300s.rules"

    if [[ -f "$rulefile" ]]; then
        echo "  udev rule OK"
    else
        echo "  Adding udev rule for G300s..."
        echo "$rule" | sudo tee "$rulefile" >/dev/null
        sudo udevadm control --reload-rules
        sudo udevadm trigger
        echo "  udev rule added. If G300s was already plugged in, replug it."
    fi
}

ensure_ready() {
    install_deps
    build_ratslap
    setup_udev
    echo ""

    # Verify G300s is connected
    if ! lsusb | grep -q "046d:c246"; then
        echo "ERROR: G300s not detected. Plug it in and try again."
        exit 1
    fi
}

# --- Remap commands ---

run_ratslap() {
    "$RATSLAP_DIR/ratslap" "$@" 2>&1
}

apply_mac() {
    echo "Applying macOS profile..."
    echo ""
    echo "  G4 (lower-left)  → Mission Control  (Ctrl+Up)"
    echo "  G5 (upper-left)  → Space Left       (Ctrl+Left)"
    echo "  G6 (lower-right) → App Exposé       (Ctrl+Down)"
    echo "  G7 (upper-right) → Space Right      (Ctrl+Right)"
    echo "  G9 (bottom)      → Page Back        (Cmd+[)"
    echo ""
    for p in $PROFILES; do
        run_ratslap --modify "$p" \
            --G4 LeftCtrl+Up \
            --G5 LeftCtrl+Left \
            --G6 LeftCtrl+Down \
            --G7 LeftCtrl+Right \
            --G9 Super_L+[ \
            | grep -E "^(Modifying|Setting|Saving)" || true
        echo "  Profile $p done"
    done
    echo ""
    echo "Done! Plug mouse into Mac."
}

apply_windows() {
    echo "Applying Windows profile..."
    echo ""
    echo "  G4 (lower-left)  → Task View        (Win+Tab)"
    echo "  G5 (upper-left)  → Desktop Left     (Win+Ctrl+Left)"
    echo "  G6 (lower-right) → Show Desktop     (Win+D)"
    echo "  G7 (upper-right) → Desktop Right    (Win+Ctrl+Right)"
    echo "  G9 (bottom)      → Page Back        (Alt+Left)"
    echo ""
    for p in $PROFILES; do
        run_ratslap --modify "$p" \
            --G4 Super_L+Tab \
            --G5 Super_L+LeftCtrl+Left \
            --G6 Super_L+D \
            --G7 Super_L+LeftCtrl+Right \
            --G9 LeftAlt+Left \
            | grep -E "^(Modifying|Setting|Saving)" || true
        echo "  Profile $p done"
    done
    echo ""
    echo "Done! Plug mouse into Windows PC."
}

show_config() {
    for p in $PROFILES; do
        run_ratslap --print "$p"
        echo ""
    done
}

reset_factory() {
    echo "Resetting to factory defaults..."
    for p in $PROFILES; do
        run_ratslap --modify "$p" \
            --G4 Button6 \
            --G5 Button7 \
            --G6 LeftCtrl+Z \
            --G7 LeftCtrl+V \
            --G9 DPICycle \
            | grep -E "^(Modifying|Setting|Saving)" || true
        echo "  Profile $p reset"
    done
    echo "Done!"
}

# --- Main ---

[[ $# -lt 1 ]] && usage

CMD="$1"
ensure_ready

case "$CMD" in
    mac)     apply_mac ;;
    windows) apply_windows ;;
    show)    show_config ;;
    reset)   reset_factory ;;
    *)       usage ;;
esac
