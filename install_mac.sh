#!/bin/bash
set -e

echo ""
echo " ============================================"
echo "  PokeParser Installer for Linux"
echo " ============================================"
echo ""

# Detect package manager
if command -v apt-get &>/dev/null; then
    PKG="apt"
elif command -v dnf &>/dev/null; then
    PKG="dnf"
elif command -v pacman &>/dev/null; then
    PKG="pacman"
else
    echo " [WARN] Unknown package manager. Install Tesseract manually."
    PKG="unknown"
fi

# ── Tesseract ──────────────────────────────────────────────────────────────────
if ! command -v tesseract &>/dev/null; then
    echo " [INFO] Installing Tesseract OCR..."
    if [ "$PKG" = "apt" ]; then
        sudo apt-get update -q && sudo apt-get install -y tesseract-ocr python3-tk
    elif [ "$PKG" = "dnf" ]; then
        sudo dnf install -y tesseract python3-tkinter
    elif [ "$PKG" = "pacman" ]; then
        sudo pacman -S --noconfirm tesseract tk
    fi
else
    echo " [OK] Tesseract found: $(tesseract --version 2>&1 | head -1)"
fi

# ── Python packages ────────────────────────────────────────────────────────────
echo ""
echo " [INFO] Installing Python packages..."
python3 -m pip install --upgrade pip --quiet --break-system-packages 2>/dev/null || \
python3 -m pip install --upgrade pip --quiet
python3 -m pip install \
    pillow pytesseract numpy openpyxl \
    google-api-python-client google-auth-httplib2 google-auth-oauthlib \
    requests tkinterdnd2 pyinstaller \
    --quiet --break-system-packages 2>/dev/null || \
python3 -m pip install \
    pillow pytesseract numpy openpyxl \
    google-api-python-client google-auth-httplib2 google-auth-oauthlib \
    requests tkinterdnd2 pyinstaller --quiet
echo " [OK] Python packages installed."

# ── Build ──────────────────────────────────────────────────────────────────────
echo ""
echo " [INFO] Building PokeParser binary (60-90 seconds)..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

python3 -m PyInstaller pokeparser.spec --noconfirm --clean

# ── Desktop entry ──────────────────────────────────────────────────────────────
DESKTOP_FILE="$HOME/.local/share/applications/pokeparser.desktop"
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=PokeParser
Comment=PokeNexus Screenshot OCR Tool
Exec=$SCRIPT_DIR/dist/PokeParser/PokeParser
Icon=$SCRIPT_DIR/assets/icon.png
Terminal=false
Type=Application
Categories=Utility;
EOF
chmod +x "$DESKTOP_FILE"

echo ""
echo " ============================================"
echo "  Installation Complete!"
echo " ============================================"
echo ""
echo " Binary: $SCRIPT_DIR/dist/PokeParser/PokeParser"
echo " Desktop shortcut created."
echo ""
