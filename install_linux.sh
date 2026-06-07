# Installing PokeParser

## Quick Install (Windows)

1. **Install Tesseract OCR** — the engine that reads screenshots
   - Download: [tesseract-ocr-w64-setup-5.3.3.exe](https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe)
   - Run the installer, keep the default path (`C:\Program Files\Tesseract-OCR\`)

2. **Download PokeParser** from the [latest Release](../../releases/latest)
   - Download `PokeParser-Windows.zip`
   - Unzip it anywhere (Desktop, Downloads, wherever)
   - Double-click `PokeParser.exe`

That's it. No Python, no setup, no installer.

---

## Quick Install (macOS)

1. **Install Tesseract**
   ```bash
   brew install tesseract
   ```
   (If you don't have Homebrew: [brew.sh](https://brew.sh))

2. **Download PokeParser** from the [latest Release](../../releases/latest)
   - Download `PokeParser-Mac.zip`
   - Unzip it
   - Double-click `PokeParser.app`

   If macOS blocks it: **System Settings → Privacy & Security → Open Anyway**

---

## Quick Install (Linux)

1. **Install Tesseract**
   ```bash
   sudo apt install tesseract-ocr        # Ubuntu / Debian
   sudo dnf install tesseract             # Fedora
   sudo pacman -S tesseract               # Arch
   ```

2. **Download PokeParser** from the [latest Release](../../releases/latest)
   - Download `PokeParser-Linux.zip`
   - Unzip it
   - Run `./PokeParser` from the unzipped folder

---

## Usage

1. Launch PokeParser
2. Drop your PokeNexus screenshots onto the queue (or use **+ Files** / **+ Folder**)
3. Click **▶ Parse Screenshots**
4. Click **💾 Save Locally** or **☁ Upload to Drive**

### Screenshot naming

The app reads the Pokemon name, level, and shiny status directly from the in-game
label — no strict file naming required. These conventions make it work better:

| Situation | Example filename |
|---|---|
| Shiny | `S Gengar.png` or `S_Gengar.png` |
| Specialty form | `Chandelure-Halloween.png` |
| Multiple same species | `Abra 1.png`, `Abra 2.png` |
| Anything else | Works — falls back to filename |

### Output

Each run produces a timestamped `.xlsx` file:
- IV cells **green** when 30 or 31
- Nature cell **green** when Smogon (USUM Gen 7) recommends it for that species
- `Parse Errors` column flags anything the OCR couldn't read cleanly

---

## Google Drive (optional)

To have results upload directly to your Drive:

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project → Enable **Google Drive API**
3. Credentials → Create → **OAuth 2.0 Client ID** → Desktop App
4. Download `credentials.json`
5. In PokeParser: **☁ Drive Setup** → load the file → Authorise

One-time setup per machine. Your token is saved locally — you won't be asked again.

---

## Building from Source

If you'd rather build it yourself (or want to make changes):

1. Install [Python 3.10+](https://python.org) — check **Add Python to PATH**
2. Install Tesseract (see above)
3. Clone or download this repository
4. Run the installer for your platform:
   - **Windows:** double-click `install_windows.bat`
   - **macOS:** `bash install_mac.sh`
   - **Linux:** `bash install_linux.sh`

The installer handles all Python dependencies and builds the app.
Output lands in `dist\PokeParser\` (Windows/Linux) or `dist/PokeParser.app` (macOS).

---

## Troubleshooting

**"Tesseract not found" on startup**
Tesseract isn't installed or isn't at the default path. Reinstall it and keep
the default path (`C:\Program Files\Tesseract-OCR\` on Windows).

**Level is blank for some Pokemon**
Affects ~8 screenshot types where an animated game background completely
covers the left panel. All IVs, EVs, nature, and other fields still parse correctly.

**Pokemon name shows filename instead of in-game name**
The `Parse Errors` column will say `name_from_filename`. This happens when
the background is too busy for the name label to be readable. Rename the file
to the Pokemon's name and re-parse to fix it.

**Settings or Drive Setup won't open**
Check the log panel for an error message. Usually means a missing dependency —
re-run the installer to repair.
