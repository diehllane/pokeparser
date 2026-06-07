# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# Collect tkinterdnd2 completely (includes platform native libs)
dnd_datas, dnd_binaries, dnd_hiddenimports = collect_all('tkinterdnd2')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=dnd_binaries,
    datas=dnd_datas + [('assets', 'assets')],
    hiddenimports=dnd_hiddenimports + [
        'PIL', 'PIL._tkinter_finder', 'PIL._imaging',
        'pytesseract',
        'numpy', 'numpy.core._multiarray_umath',
        'openpyxl', 'openpyxl.cell._writer',
        'googleapiclient', 'googleapiclient.discovery',
        'google.auth', 'google.auth.transport.requests',
        'google.oauth2', 'google.oauth2.credentials',
        'google_auth_oauthlib', 'google_auth_oauthlib.flow',
        'google.auth.transport',
        'requests', 'urllib3', 'certifi',
        'tkinter', 'tkinter.ttk', 'tkinter.filedialog',
        'tkinter.messagebox',
        'ocr_engine', 'spreadsheet', 'smogon_lookup',
        'gdrive', 'settings',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'pandas', 'IPython', 'jupyter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PokeParser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if sys.platform == 'win32' else
         'assets/icon.icns' if sys.platform == 'darwin' else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PokeParser',
)

# macOS: also build a .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='PokeParser.app',
        icon='assets/icon.icns',
        bundle_identifier='com.pokeparser.app',
        info_plist={
            'CFBundleName': 'PokeParser',
            'CFBundleDisplayName': 'PokeParser',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0',
            'NSHighResolutionCapable': True,
        },
    )
