from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.simulation import _top_down_slot_layout


WIDTH = 1600
HEIGHT = 900
OUT = ROOT / "app/static/assets/generated/parking-topdown-background-v1.png"


def pct(point: tuple[float, float]) -> tuple[int, int]:
    x, y = point
    return int(WIDTH * x / 100), int(HEIGHT * y / 100)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Courier New.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def centered(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, fill: tuple[int, int, int], size: int, bold: bool = True) -> None:
    text_font = font(size, bold)
    bbox = draw.textbbox((0, 0), text, font=text_font)
    x = box[0] + (box[2] - box[0] - (bbox[2] - bbox[0])) // 2
    y = box[1] + (box[3] - box[1] - (bbox[3] - bbox[1])) // 2
    draw.text((x, y), text, fill=fill, font=text_font)


def draw_arrow(draw: ImageDraw.ImageDraw, center: tuple[float, float], direction: str, fill: tuple[int, int, int]) -> None:
    cx, cy = pct(center)
    r = 28
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 236, 145), outline=(78, 75, 57), width=3)
    symbol = {"right": ">", "left": "<", "down": "v", "up": "^"}[direction]
    centered(draw, (cx - r, cy - r - 3, cx + r, cy + r - 3), symbol, fill, 34, True)


def draw_slot(draw: ImageDraw.ImageDraw, x_pct: float, y_pct: float, angle: float, motorcycle: bool = False) -> None:
    cx, cy = pct((x_pct, y_pct))
    w, h = (32, 58) if not motorcycle else (23, 42)
    color = (246, 246, 240) if not motorcycle else (91, 235, 181)
    if angle in {90, 270}:
        w, h = h, w
    draw.rectangle((cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2), outline=color, width=3)
    if angle in {0, 180}:
        draw.line((cx - w // 2, cy - h // 2, cx + w // 2, cy - h // 2), fill=(143, 143, 141), width=4)
    else:
        draw.line((cx - w // 2, cy - h // 2, cx - w // 2, cy + h // 2), fill=(143, 143, 141), width=4)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (WIDTH, HEIGHT), (216, 217, 214))
    draw = ImageDraw.Draw(image)

    lot = (70, 55, WIDTH - 70, HEIGHT - 55)
    draw.rounded_rectangle(lot, radius=18, fill=(143, 143, 141), outline=(238, 238, 232), width=8)

    draw.rectangle((lot[0], lot[1], lot[0] + 185, lot[3]), fill=(128, 156, 137))
    draw.rectangle((lot[2] - 245, lot[1], lot[2], lot[3]), fill=(154, 131, 129))

    entry = (lot[0] + 28, int(HEIGHT * 0.38), lot[0] + 210, int(HEIGHT * 0.57))
    exit_box = (lot[2] - 210, int(HEIGHT * 0.40), lot[2] - 28, int(HEIGHT * 0.59))
    draw.rectangle(entry, fill=(102, 201, 123), outline=(246, 246, 240), width=5)
    draw.rectangle(exit_box, fill=(218, 91, 86), outline=(246, 246, 240), width=5)
    centered(draw, (entry[0], entry[1], entry[0] + 130, entry[3]), "MAIN\nENTRY", (18, 47, 25), 25, True)
    centered(draw, (exit_box[0] + 64, exit_box[1], exit_box[2], exit_box[3]), "EXIT\nTO ROAD", (61, 12, 12), 24, True)

    mall = (int(WIDTH * 0.28), int(HEIGHT * 0.07), int(WIDTH * 0.68), int(HEIGHT * 0.17))
    draw.rectangle(mall, fill=(193, 194, 190), outline=(238, 238, 232), width=5)
    centered(draw, mall, "MALL", (113, 113, 109), 26, True)

    # Drive aisles, intentionally left open so moving vehicles do not cover labels.
    draw.rectangle((int(WIDTH * 0.14), int(HEIGHT * 0.46), int(WIDTH * 0.87), int(HEIGHT * 0.55)), outline=(238, 238, 232), width=5)
    draw.rectangle((int(WIDTH * 0.14), int(HEIGHT * 0.70), int(WIDTH * 0.87), int(HEIGHT * 0.78)), outline=(238, 238, 232), width=5)
    draw.rectangle((int(WIDTH * 0.76), int(HEIGHT * 0.46), int(WIDTH * 0.79), int(HEIGHT * 0.78)), outline=(238, 238, 232), width=5)

    label_font = font(22, True)
    small_font = font(17, True)
    draw.text(pct((14, 36)), "TICKET GATE", fill=(24, 75, 37), font=small_font)
    draw.text(pct((37, 40)), "ONE-WAY SEARCH LOOP", fill=(58, 58, 55), font=label_font)
    draw.text(pct((27, 21)), "CAR PARKING ROW A", fill=(58, 58, 55), font=small_font)
    draw.text(pct((24, 40)), "CAR PARKING ROW B", fill=(58, 58, 55), font=small_font)
    draw.text(pct((20, 65)), "CAR PARKING ROW C", fill=(58, 58, 55), font=small_font)
    draw.text(pct((82, 21)), "MOTORCYCLE PARKING", fill=(15, 96, 75), font=small_font)
    draw.text(pct((5, 83)), "ENTRY QUEUE", fill=(50, 55, 52), font=small_font)
    draw.text(pct((87, 83)), "EXIT FLOW", fill=(50, 55, 52), font=small_font)

    for center, direction in [((21, 50), "right"), ((43, 50), "right"), ((76, 58), "down"), ((43, 74), "left"), ((78, 50), "right")]:
        draw_arrow(draw, center, direction, (24, 24, 22))

    slots = _top_down_slot_layout()
    for index, slot in enumerate(slots):
        draw_slot(draw, slot["x"], slot["y"], slot["angle"], motorcycle=slot["slot_type"] == "motorcycle_slot")

    # Queue/exit lane markers sit away from moving path labels.
    draw.line((pct((4, 24))[0], pct((4, 24))[1], pct((4, 78))[0], pct((4, 78))[1]), fill=(238, 238, 232), width=3)
    draw.line((pct((10, 24))[0], pct((10, 24))[1], pct((10, 78))[0], pct((10, 78))[1]), fill=(238, 238, 232), width=3)
    draw.line((pct((91, 61))[0], pct((91, 61))[1], pct((91, 86))[0], pct((91, 86))[1]), fill=(238, 238, 232), width=3)
    draw.line((pct((98, 61))[0], pct((98, 61))[1], pct((98, 86))[0], pct((98, 86))[1]), fill=(238, 238, 232), width=3)

    image.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
