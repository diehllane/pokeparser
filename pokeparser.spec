"""
PokeParser OCR Engine  —  v5
Accuracy improvements:
- Multi-threshold sweep for info bands (picks cleanest Pokédex read)
- Pokédex constrained to 1-999 range
- "S " (S-space) filename prefix detected as shiny alongside "S_"
- Numbered duplicates (Abra_1, Togepi_2) stripped from filename fallback
"""

import os
import re
import platform
import numpy as np
import pytesseract
from PIL import Image, ImageOps

# ── Tesseract path (frozen app fix) ───────────────────────────────────────────
def _find_tesseract():
    try:
        pytesseract.get_tesseract_version()
        return
    except Exception:
        pass
    if platform.system() == "Windows":
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
    elif platform.system() == "Darwin":
        candidates = ["/usr/local/bin/tesseract", "/opt/homebrew/bin/tesseract"]
    else:
        candidates = ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]
    for p in candidates:
        if os.path.isfile(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return

_find_tesseract()

# ── Constants ──────────────────────────────────────────────────────────────────

NATURES = {
    "Hardy","Lonely","Brave","Adamant","Naughty",
    "Bold","Docile","Relaxed","Impish","Lax",
    "Timid","Hasty","Serious","Jolly","Naive",
    "Modest","Mild","Quiet","Bashful","Rash",
    "Calm","Gentle","Sassy","Careful","Quirky",
}

HAPPINESS_VALUES = {70, 255, 184, 141, 242, 125}

# Matches "Lv 25 [S]Gengar" and all mangled shiny variants:
# |SJ, [S/, [S|, (S], etc. that Tesseract produces from the [S] marker.
_LV_PATTERN = re.compile(
    r"[Ll][Vv][Yy]?\s*(\d+)\s*"
    r"(?:[^A-Za-z0-9]{0,2}[Ss][^A-Za-z0-9]{0,2})?"   # optional shiny marker
    r"([A-Z][A-Za-z0-9\-]+(?:[- ][A-Z][A-Za-z0-9]+)*)",
    re.IGNORECASE,
)
_SHINY_MARKER = re.compile(
    r"[\[\(|][Ss][\]\)/|Jj]|\[S|\(S",
    re.IGNORECASE,
)

# ── Column detection ───────────────────────────────────────────────────────────

def _find_value_col_x(arr: np.ndarray) -> int:
    h, w = arr.shape[:2]
    for x in range(w // 2, w):
        col = arr[80:200, x, :]
        gray_cnt = (
            (np.abs(col[:, 0].astype(int) - col[:, 1].astype(int)) < 8) &
            (np.abs(col[:, 1].astype(int) - col[:, 2].astype(int)) < 8) &
            (col[:, 0] > 65) & (col[:, 0] < 110)
        ).sum()
        if gray_cnt > 30:
            return x
    return int(w * 0.66)


def _find_value_col_right(arr: np.ndarray, val_x: int) -> int:
    """
    Find the rightmost x of the gray value column.
    Prevents UI decoration (e.g. machine graphics at image right edge)
    from bleeding into stat band crops and confusing Tesseract.
    """
    h, w = arr.shape[:2]
    y1, y2 = int(h * 0.15), int(h * 0.60)
    for x in range(min(w - 1, val_x + 200), val_x + 50, -1):
        col = arr[y1:y2, x, :]
        gray_cnt = (
            (np.abs(col[:, 0].astype(int) - col[:, 1].astype(int)) < 12) &
            (np.abs(col[:, 1].astype(int) - col[:, 2].astype(int)) < 12) &
            (col[:, 0] > 60) & (col[:, 0] < 115)
        ).sum()
        if gray_cnt > (y2 - y1) * 0.3:
            return x + 8
    return w


def _find_row_bands(arr: np.ndarray, val_x: int) -> list:
    h = arr.shape[0]
    strip = arr[:, val_x: val_x + 15, :]
    brightness = strip.mean(axis=(1, 2))
    bands = []
    in_band = False
    band_start = 0
    for y in range(70, h - 50):
        b = brightness[y]
        if b > 60 and not in_band:
            in_band = True
            band_start = y
        elif b < 40 and in_band:
            if y - band_start > 10:
                bands.append((band_start, y))
            in_band = False
    if in_band and (h - 50) - band_start > 10:
        bands.append((band_start, h - 50))
    return bands


def _ocr_band(img: Image.Image, arr: np.ndarray, y1: int, y2: int,
              val_x: int, scale: int = 8, threshold: int = 120,
              val_right: int = None) -> str:
    w = arr.shape[1]
    x_right = val_right if val_right is not None else w
    row = img.crop((val_x - 5, y1 - 1, x_right, y2 + 1))
    row_big = row.resize((row.width * scale, row.height * scale), Image.LANCZOS)
    row_gray = row_big.convert("L")
    row_thresh = row_gray.point(lambda px: 0 if px > threshold else 255, "1")
    text = pytesseract.image_to_string(row_thresh, config="--psm 7 --oem 3")
    return text.strip()


def _ocr_band_best_thresh(img: Image.Image, arr: np.ndarray, y1: int, y2: int,
                          val_x: int) -> tuple:
    """
    Try multiple thresholds for an info band. Returns (raw_text, best_number).
    Picks the read that gives the largest valid Pokédex number (1-999)
    with the least noise. Used for the Pokédex band specifically.
    """
    w = arr.shape[1]
    row = img.crop((val_x - 5, y1 - 1, w, y2 + 1))
    big = row.resize((row.width * 8, row.height * 8), Image.LANCZOS)
    gray = big.convert("L")

    candidates = []
    for thresh in [110, 120, 125, 130, 135, 140]:
        t = gray.point(lambda px, th=thresh: 0 if px > th else 255, "1")
        text = pytesseract.image_to_string(t, config="--psm 7 --oem 3").strip()
        nums = [int(x) for x in re.findall(r"\d+", text)]
        noise = len(re.sub(r"[\d\s\.\,\!\|\[\]\(\)\-]", "", text))
        valid = [n for n in nums if 1 <= n <= 999]
        if valid:
            best_num = max(valid, key=lambda x: len(str(x)))
            candidates.append((len(str(best_num)), -noise, thresh, best_num, text))

    if not candidates:
        return "", None
    candidates.sort(reverse=True)
    return candidates[0][4], candidates[0][3]


# ── Left panel ─────────────────────────────────────────────────────────────────

def _ocr_left_panel(img: Image.Image, arr: np.ndarray) -> str:
    h, w = arr.shape[:2]
    for y_start, y_end in [(0.45, 0.78), (0.48, 0.75), (0.52, 0.82)]:
        area = img.crop((0, int(h * y_start), int(w * 0.65), int(h * y_end)))
        area_big = area.resize((area.width * 5, area.height * 5), Image.LANCZOS)
        inv = ImageOps.invert(area_big.convert("L"))
        thresh = inv.point(lambda px: 255 if px > 90 else 0, "1")
        text = pytesseract.image_to_string(thresh, config="--psm 6 --oem 3")
        if re.search(r"[Ll][Vv]", text):
            return text.strip()
    return ""


def _parse_filename(filepath: str) -> tuple:
    """
    Extract (pokemon_name, shiny) from filename.
    Handles: S_Name.png, S Name.png (S-space), Name_1.png (numbered duplicate)
    """
    fname = os.path.splitext(os.path.basename(filepath))[0]

    # Detect shiny: "S_" prefix OR "S " prefix (space-separated on Windows)
    shiny = False
    if fname.startswith("S_"):
        shiny = True
        fname = fname[2:]
    elif fname.startswith("S "):
        shiny = True
        fname = fname[2:]

    # Strip trailing _N or -N numbering (Abra_1, Togepi_2, etc.)
    fname = re.sub(r"[_\-]\d+$", "", fname)

    # Underscored suffixes → hyphenated (Halloween, Christmas)
    pokemon = fname.replace("_", "-")
    return pokemon, shiny


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_nums(s: str) -> list:
    return [int(x) for x in re.findall(r"\d+", s)]


def _clean_word(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9 '\-]", "", s).strip()


def _clean_name(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9\- '.]", "", s).strip()
    s = re.sub(r"\s+[a-z]$", "", s)
    return s.strip()


def _find_hp_band(band_texts: list) -> int:
    hp_re = re.compile(r"\d+\s*[/f7|i1]\s*\d+\s*[\(\[]\d+[\)\]]")
    for i, t in enumerate(band_texts):
        if hp_re.search(t):
            return i
    slash_re = re.compile(r"(\d+)\s*[/f7|i1]\s*(\d+)")
    for i, t in enumerate(band_texts):
        m = slash_re.search(t)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a == b and a < 2000:
                return i
    return -1


def _find_dex_band(band_texts: list, hp_idx: int) -> int:
    for i, t in enumerate(band_texts[:10]):
        nums = _extract_nums(t)
        alpha_words = re.findall(r"[A-Za-z]{4,}", t)
        is_happiness = (
            nums and nums[0] in HAPPINESS_VALUES
            and not alpha_words
            and len(t.strip()) < 10
        )
        if not is_happiness:
            continue
        if i >= 1:
            nature_band = band_texts[i - 1] if i - 1 < len(band_texts) else ""
            nature_words = re.findall(r"[A-Za-z]+", nature_band)
            if any(w.capitalize() in NATURES for w in nature_words):
                return max(0, i - 3)
    if hp_idx >= 6:
        return hp_idx - 6
    for i, t in enumerate(band_texts[:8]):
        nums = _extract_nums(t)
        alpha = re.findall(r"[A-Za-z]{3,}", t)
        if nums and nums[0] <= 999 and not alpha:
            return i
    return 0


# ── Main Parser ────────────────────────────────────────────────────────────────

def parse_screenshot(image_path: str) -> dict:
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img)

    val_x = _find_value_col_x(arr)
    val_right = _find_value_col_right(arr, val_x)
    bands = _find_row_bands(arr, val_x)

    band_texts = [
        _ocr_band(img, arr, y1, y2, val_x, scale=8, threshold=120)
        for y1, y2 in bands
    ]

    hp_idx = _find_hp_band(band_texts)
    dex_idx = _find_dex_band(band_texts, hp_idx)

    if hp_idx >= 0:
        for offset in range(7):
            idx = hp_idx + offset
            if idx < len(bands):
                y1, y2 = bands[idx]
                band_texts[idx] = _ocr_band(img, arr, y1, y2, val_x,
                                             scale=12, threshold=120,
                                             val_right=val_right)

    result = {
        "file": os.path.basename(image_path),
        "pokemon": None, "level": None, "shiny": False,
        "name_source": "ocr",
        "pokedex": None, "type": None, "nature": None,
        "happiness": None, "ability": None, "catcher": None,
        "hp_current": None, "hp_max": None, "hp_iv": None, "hp_ev": None,

        "atk": None, "atk_iv": None, "atk_ev": None,
        "def": None, "def_iv": None, "def_ev": None,
        "spec_atk": None, "spec_atk_iv": None, "spec_atk_ev": None,
        "spec_def": None, "spec_def_iv": None, "spec_def_ev": None,
        "speed": None, "speed_iv": None, "speed_ev": None,
        "parse_errors": [],
    }

    # ── Name + level ──────────────────────────────────────────────────────────
    left_text = _ocr_left_panel(img, arr)
    ocr_name_found = False
    for line in left_text.splitlines():
        m = _LV_PATTERN.search(line)
        if m:
            result["level"] = int(m.group(1))
            result["shiny"] = bool(_SHINY_MARKER.search(line))
            # Strip any leading non-alpha leakage from shiny marker (e.g. 'JAzumarill')
            raw_name = m.group(2).strip()
            clean = re.sub(r"^[^A-Z]+", "", raw_name)
            result["pokemon"] = _clean_name(clean if clean else raw_name)
            ocr_name_found = True
            break

    fn_pokemon, fn_shiny = _parse_filename(image_path)
    # S_ or "S " filename prefix is a strong hint for shiny — use it
    # even if OCR didn't find [S] (e.g. busy background hid the name line)
    if fn_shiny:
        result["shiny"] = True
    # Only fall back to filename for the pokemon name if OCR couldn't read it
    if not ocr_name_found or not result["pokemon"]:
        result["pokemon"] = fn_pokemon
        result["name_source"] = "filename"
        # Note in errors but don't treat as critical — filename is reliable
        result["parse_errors"].append("name_from_filename")
    if result["level"] is None:
        result["parse_errors"].append("level")

    def _get(idx: int) -> str:
        return band_texts[idx] if 0 <= idx < len(band_texts) else ""

    # ── Pokédex — multi-threshold sweep ───────────────────────────────────────
    if dex_idx < len(bands):
        y1, y2 = bands[dex_idx]
        _, dex_num = _ocr_band_best_thresh(img, arr, y1, y2, val_x)
        result["pokedex"] = dex_num
    if not result["pokedex"]:
        result["parse_errors"].append("pokedex")

    # ── Type, Nature, Happiness, Ability, Catcher ────────────────────────────
    result["type"] = _clean_word(_get(dex_idx + 1))

    n = _clean_word(_get(dex_idx + 2))
    for nat in NATURES:
        if nat.lower() in n.lower():
            result["nature"] = nat
            break
    if not result["nature"]:
        result["parse_errors"].append("nature")

    h_nums = _extract_nums(_get(dex_idx + 3))
    result["happiness"] = h_nums[0] if h_nums else None
    result["ability"] = _clean_word(_get(dex_idx + 4))
    result["catcher"] = _clean_word(_get(dex_idx + 5))

    # ── Stat bands ────────────────────────────────────────────────────────────
    if hp_idx < 0:
        result["parse_errors"].append("hp")
    else:
        hp_nums = _extract_nums(_get(hp_idx))
        if len(hp_nums) >= 4:
            result["hp_current"], result["hp_max"] = hp_nums[0], hp_nums[1]
            result["hp_iv"], result["hp_ev"] = hp_nums[2], hp_nums[3]
        elif len(hp_nums) == 3:
            result["hp_current"], result["hp_max"] = hp_nums[0], hp_nums[1]
            result["hp_iv"], result["hp_ev"] = hp_nums[2], 0
        else:
            result["parse_errors"].append("hp")

        # Exp excluded — long numbers with commas OCR unreliably
        result["exp"] = None

        for stat_name, offset in [("atk", 2), ("def", 3), ("spec_atk", 4),
                                   ("spec_def", 5), ("speed", 6)]:
            nums = _extract_nums(_get(hp_idx + offset))
            if len(nums) >= 3:
                result[stat_name] = nums[0]
                result[f"{stat_name}_iv"] = nums[1]
                result[f"{stat_name}_ev"] = nums[2]
            elif len(nums) == 2:
                result[stat_name] = nums[0]
                result[f"{stat_name}_iv"] = nums[1]
                result[f"{stat_name}_ev"] = 0
            else:
                result["parse_errors"].append(stat_name)

    return result
