#!/bin/bash
set -e

echo ""
echo " ============================================"
echo "  PokeParser Installer for macOS"
echo " ============================================"
echo ""

# ── Check Homebrew ─────────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
    echo " [INFO] Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add to PATH for Apple Silicon
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo " [OK] Homebrew found."
fi

# ── Check Python ───────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo " [INFO] Installing Python..."
    brew install python
fi
PYVER=$(python3 --version 2>&1)
echo " [OK] $PYVER found."

# ── Check Tesseract ────────────────────────────────────────────────────────────
if ! command -v tesseract &>/dev/null; then
    echo " [INFO] Installing Tesseract OCR..."
    brew install tesseract
else
    echo " [OK] Tesseract found: $(tesseract --version 2>&1 | head -1)"
fi

# ── Python packages ────────────────────────────────────────────────────────────
echo ""
echo " [INFO] Installing Python packages..."
python3 -m pip install --upgrade pip --quiet
python3 -m pip install \
    pillow pytesseract numpy openpyxl \
    google-api-python-client google-auth-httplib2 google-auth-oauthlib \
    requests tkinterdnd2 pyinstaller --quiet
echo " [OK] Python packages installed."

# ── Build .app ─────────────────────────────────────────────────────────────────
echo ""
echo " [INFO] Building PokeParser.app (60-90 seconds)..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

python3 -m PyInstaller pokeparser.spec --noconfirm --clean

# ── Move to Applications ───────────────────────────────────────────────────────
APP="$SCRIPT_DIR/dist/PokeParser.app"
DEST="/Applications/PokeParser.app"

if [ -d "$APP" ]; then
    echo ""
    echo " [INFO] Moving to /Applications..."
    rm -rf "$DEST" 2>/dev/null || true
    cp -r "$APP" "$DEST"
    
    # Remove quarantine flag
    xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true
    
    echo " [OK] Installed to /Applications/PokeParser.app"
    echo ""
    echo " Creating alias on Desktop..."
    osascript -e 'tell application "Finder" to make alias file \
        to POSIX file "/Applications/PokeParser.app" \
        at POSIX file (POSIX path of (path to desktop folder))' 2>/dev/null || true
fi

echo ""
echo " ============================================"
echo "  Installation Complete!"
echo " ============================================"
echo ""
echo " PokeParser is in your Applications folder."
echo " An alias has been added to your Desktop."
echo ""
echo " If macOS blocks the app: System Settings →"
echo " Privacy & Security → Open Anyway"
echo ""
