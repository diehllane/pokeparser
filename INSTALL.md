# Putting PokeParser on GitHub

## One-time repo setup

1. Go to **github.com** → sign in → click **+** (top right) → **New repository**
2. Name: `PokeParser`
3. Description: `PokeNexus screenshot OCR → Excel spreadsheet`
4. Set to **Public**
5. Leave everything else unchecked — click **Create repository**

GitHub shows you an empty repo page. Now upload the source files:

6. Click **uploading an existing file** (the link in the middle of the page)
7. Drag in everything from your unzipped `PokeParser-2026-06-06.zip` folder:
   - `main.py`
   - `ocr_engine.py`
   - `spreadsheet.py`
   - `smogon_lookup.py`
   - `gdrive.py`
   - `settings.py`
   - `requirements.txt`
   - `pokeparser.spec`
   - `install_windows.bat`
   - `install_mac.sh`
   - `install_linux.sh`
   - `README.md`
   - `INSTALL.md`
   - The `assets/` folder (icon files)
8. Scroll down → **Commit changes**

Your repo is live.

---

## Creating a Release (attach the built exe/app)

Do this after running `install_windows.bat` on Windows (and on Mac if you have one).

1. On your repo page click **Releases** (right sidebar) → **Draft a new release**
2. Click **Choose a tag** → type `v1.0` → click **Create new tag: v1.0**
3. Title: `PokeParser v1.0`
4. Description (copy/paste):
   ```
   First release.
   
   Download the zip for your platform, unzip, and run.
   Requires Tesseract OCR — see INSTALL.md for setup.
   ```
5. Under **Attach binaries**, drag in your built zips:
   - `PokeParser-Windows.zip` — the zipped `dist\PokeParser\` folder from Windows
   - `PokeParser-Mac.zip` — the zipped `PokeParser.app` from Mac (if you have one)
   - `PokeParser-Linux.zip` — already provided
6. Click **Publish release**

The download links in `INSTALL.md` and `README.md` point to
`../../releases/latest` which always resolves to the newest release automatically.

---

## Sharing with players

Send them this link (replace `YOURUSERNAME`):
```
https://github.com/YOURUSERNAME/PokeParser/blob/main/INSTALL.md
```

Or just the releases page:
```
https://github.com/YOURUSERNAME/PokeParser/releases/latest
```

---

## Updating later

When you make changes:
1. Upload the changed `.py` files to the repo (drag and drop, same as before)
2. Build a new exe on Windows
3. Draft a new release → tag `v1.1` → attach the new zip → publish

The `releases/latest` link players already have will automatically point to the new version.
