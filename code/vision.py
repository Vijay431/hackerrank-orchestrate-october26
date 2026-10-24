"""Screenshot reading: crop the table and detail panel into tiles, transcribe each tile with the model.

The model misreads a full 1800px screenshot, but reads narrow upscaled tiles accurately, so each PNG is
cut into three table column bands and a detail panel. Transcripts are cached per file under .cache/evidence.
"""
import io
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image

import prompt_registry

PROMPT = prompt_registry.load("image_tile")
NAV_WIDTH = 222          # left navigation rail
TABLE_BOX = (246, 365, 1412)      # x0, y_top, x1 of the main table body
PANEL_BOX = (1426, 330, 1776)     # x0, y_top, x1 of the detail panel
BANDS = 3
MAX_GAP = 120            # blank rows that end the content


def content_bottom(img: Image.Image, x0: int, y0: int, x1: int) -> int:
    """First y at or after y0 where MAX_GAP consecutive blank rows follow the last content row."""
    gray = img.convert("L").crop((x0, y0, x1, img.height))
    w, h = gray.size
    px = gray.load()
    last, gap = 0, 0
    for y in range(h):
        base = px[0, y]
        busy = any(abs(px[x, y] - base) > 40 for x in range(0, w, 2))
        if busy:
            last, gap = y, 0
        else:
            gap += 1
            if gap > MAX_GAP:
                break
    return y0 + last + 6


def tiles(path: Path) -> List[Tuple[str, bytes]]:
    img = Image.open(path).convert("RGB")
    out = []
    x0, y0, x1 = TABLE_BOX
    bottom = min(content_bottom(img, x0, y0, x1), img.height)
    step = (x1 - x0) // BANDS
    for i in range(BANDS):
        band = img.crop((x0 + i * step - (6 if i else 0), y0, x0 + (i + 1) * step + 6, bottom))
        if has_text(band):
            out.append((f"band{i}", _png(band, 3)))
    px0, py0, px1 = PANEL_BOX
    pbottom = min(content_bottom(img, px0, py0, px1), img.height)
    panel = img.crop((px0, py0, px1, pbottom))
    if has_text(panel):
        out.append(("panel", _png(panel, 2)))
    return out


def has_text(im: Image.Image) -> bool:
    """False for tiles that hold only background, row stripes and borders (the model returns nothing for them)."""
    gray = im.convert("L")
    lo, hi = gray.getextrema()
    hist = gray.histogram()
    median = next(i for i, _ in enumerate(hist) if sum(hist[:i + 1]) >= gray.width * gray.height / 2)
    return sum(c for i, c in enumerate(hist) if abs(i - median) > 70) > 30


def _png(im: Image.Image, scale: int) -> bytes:
    im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def transcribe(path: Path, client, scratch: Path) -> Dict[str, str]:
    """Tile name -> transcribed text; one cached model call per tile."""
    scratch.mkdir(parents=True, exist_ok=True)
    result = {}
    for name, data in tiles(path):
        tile_path = scratch / f"{path.stem}_{name}.png"
        tile_path.write_bytes(data)
        result[name] = client.complete(PROMPT, "Transcribe this region.", tile_path, purpose="image_extraction").strip()
    return result
