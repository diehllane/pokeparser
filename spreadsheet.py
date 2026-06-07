"""
smogon_lookup.py
Fetches recommended natures for a Pokemon from Smogon's USUM (Gen 7) dex.
Results are cached in memory per session.

Specialty forms (Halloween, Christmas, etc.) are looked up using their BASE species,
since they don't exist on Smogon. Competitive formes (Deoxys-Attack, Hoopa-Unbound,
Kyurem-White) are looked up as-is since Smogon has separate analyses for them.
"""

import re
import urllib.request
from functools import lru_cache

SMOGON_BASE = "https://www.smogon.com/dex/sm/pokemon/{slug}/"

# PokeNexus specialty skin suffixes that should be stripped before Smogon lookup
SPECIALTY_SUFFIXES = re.compile(
    r"-(christmas|halloween|summer|winter|spring|autumn|easter|birthday)$",
    re.IGNORECASE,
)


def get_recommended_natures(pokemon_name: str) -> set:
    """
    Return a set of nature strings recommended by Smogon (USUM/Gen 7).
    Strips specialty suffixes before lookup; caches results per session.
    Returns empty set on network failure or unknown Pokemon.
    """
    slug = _to_slug(pokemon_name)
    return _fetch_natures(slug)


@lru_cache(maxsize=256)
def _fetch_natures(slug: str) -> set:
    url = SMOGON_BASE.format(slug=slug)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PokeParser/2.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        return _parse_natures_from_html(html)
    except Exception:
        return set()


def _to_slug(name: str) -> str:
    """Convert Pokemon name to Smogon URL slug, stripping specialty suffixes."""
    name = name.strip()
    # Strip PokeNexus-only specialty suffixes (these don't exist on Smogon)
    name = SPECIALTY_SUFFIXES.sub("", name)
    name = name.lower()
    # Handle edge cases
    replacements = {
        "nidoran-f": "nidoran-f",
        "nidoran-m": "nidoran-m",
        "farfetch'd": "farfetchd",
        "mr. mime": "mr-mime",
        "mime jr.": "mime-jr",
        "type: null": "type-null",
        "jangmo-o": "jangmo-o",
        "hakamo-o": "hakamo-o",
        "kommo-o": "kommo-o",
    }
    if name in replacements:
        return replacements[name]
    slug = re.sub(r"[^a-z0-9\-]", "-", name)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _parse_natures_from_html(html: str) -> set:
    """Parse recommended natures from Smogon's dex page JSON blob."""
    natures = set()
    # Single nature: "nature":"Jolly"
    for m in re.compile(r'"nature"\s*:\s*"([A-Za-z]+)"').finditer(html):
        natures.add(m.group(1).capitalize())
    # Array form: "natures":["Jolly","Timid"]
    for m in re.compile(r'"natures"\s*:\s*\[([^\]]+)\]').finditer(html):
        for nat in re.findall(r'"([A-Za-z]+)"', m.group(1)):
            natures.add(nat.capitalize())
    return natures
