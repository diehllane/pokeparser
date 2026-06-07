"""
settings.py
Persistent user settings for PokeParser.
Stored as JSON in the user's home directory.
"""

import os
import json

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".pokeparser_settings.json")

DEFAULTS = {
    "gdrive_folder": "PokeParser",
    "gdrive_credentials": "",
    "output_dir": os.path.join(os.path.expanduser("~"), "Desktop"),
    "smogon_lookup": True,
}


def load() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
            return {**DEFAULTS, **data}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(settings: dict):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
