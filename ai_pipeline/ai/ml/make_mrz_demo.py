"""Generate a demo passport image that carries a VALID ICAO TD3 MRZ.

The bundled demo_artifacts have no machine-readable zone, so the real pipeline
honestly reports ``mrz: not detected``. This builds a passport-style image whose
MRZ has correct check digits (computed with the same algorithm the parser uses),
plus OCR-readable visible fields, so uploading it exercises OCR + MRZ + tampering
all the way to ``completed``.

Run:  python -m ai_pipeline.ai.ml.make_mrz_demo
"""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ai_pipeline.ai.mrz import calculate_check_digit

OUT = Path(__file__).resolve().parents[3] / "demo_artifacts"

DOC_NUMBER = "Q2714253"     # exists in server/demo_data/reference_records.json
NATIONALITY = "IND"
SURNAME = "DEMO"
GIVEN = "PERSON A"
DOB = "900415"              # YYMMDD
EXPIRY = "300101"           # YYMMDD (future -> not expired)
SEX = "M"


def _mono(size: int) -> ImageFont.FreeTypeFont:
    for path in (r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\cour.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _sans(size: int) -> ImageFont.FreeTypeFont:
    for path in (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _pad(value: str, length: int) -> str:
    return (value + "<" * length)[:length]


def build_mrz() -> tuple[str, str]:
    doc = _pad(DOC_NUMBER, 9)
    doc_c = calculate_check_digit(doc)
    dob_c = calculate_check_digit(DOB)
    exp_c = calculate_check_digit(EXPIRY)
    personal = "<" * 14
    personal_c = calculate_check_digit(personal)

    line1 = _pad(f"P<{NATIONALITY}{SURNAME}<<{GIVEN.replace(' ', '<')}", 44)
    line2_wo_composite = (
        f"{doc}{doc_c}{NATIONALITY}{DOB}{dob_c}{SEX}{EXPIRY}{exp_c}{personal}{personal_c}"
    )
    composite = calculate_check_digit(
        line2_wo_composite[0:10] + line2_wo_composite[13:20] + line2_wo_composite[21:43]
    )
    line2 = _pad(line2_wo_composite + composite, 44)
    return line1, line2


def _draw_mrz_line(draw: ImageDraw.ImageDraw, text: str, x: int, y: int,
                   font: ImageFont.FreeTypeFont, pitch: int) -> None:
    """Draw the MRZ at a fixed character pitch for clean OCR."""
    for i, ch in enumerate(text):
        draw.text((x + i * pitch, y), ch, fill=(10, 10, 10), font=font)


def render(tampered: bool = False) -> Image.Image:
    line1, line2 = build_mrz()
    W, H = 1000, 640
    img = Image.new("RGB", (W, H), (238, 240, 235))
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, W, 70], fill=(28, 60, 110))
    draw.text((24, 20), "PASSPORT", fill=(245, 245, 245), font=_sans(34))
    draw.text((W - 150, 26), NATIONALITY, fill=(245, 245, 245), font=_sans(28))

    # Photo box
    px, py, pw, ph = 40, 110, 220, 280
    photo = (np.random.normal(150, 12, (ph, pw, 3))).clip(0, 255).astype(np.uint8)
    img.paste(Image.fromarray(photo, "RGB"), (px, py))
    draw.rectangle([px, py, px + pw, py + ph], outline=(28, 60, 110), width=3)

    fields = [
        ("Surname", SURNAME),
        ("Given names", GIVEN),
        ("Passport No.", DOC_NUMBER),
        ("Nationality", NATIONALITY),
        ("Date of birth", f"15-04-1990"),
        ("Date of expiry", f"01-01-2030"),
        ("Sex", SEX),
    ]
    fx, fy = 300, 120
    for label, value in fields:
        draw.text((fx, fy), label.upper(), fill=(110, 110, 110), font=_sans(16))
        draw.text((fx, fy + 20), value, fill=(15, 15, 15), font=_sans(26))
        fy += 62

    # MRZ zone — light band, fixed-pitch OCR-B-like monospace
    draw.rectangle([0, H - 130, W, H], fill=(250, 250, 248))
    mrz_font = _mono(30)
    pitch = 21
    _draw_mrz_line(draw, line1, 26, H - 118, mrz_font, pitch)
    _draw_mrz_line(draw, line2, 26, H - 74, mrz_font, pitch)

    if tampered:
        # Overwrite the visible passport number with a mismatching value and
        # splice a low-quality recompressed patch — a genuine forgery artifact.
        draw.rectangle([fx, 120 + 2 * 62, fx + 180, 120 + 2 * 62 + 52], fill=(236, 238, 233))
        draw.text((fx, 120 + 2 * 62 + 18), "Q9999999", fill=(15, 15, 15), font=_sans(26))
        region = img.crop((px, py, px + pw, py + ph))
        buf = io.BytesIO()
        region.save(buf, format="JPEG", quality=18)
        buf.seek(0)
        img.paste(Image.open(buf).convert("RGB"), (px, py))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    genuine_path = OUT / f"synthetic_mrz_passport_original_{DOC_NUMBER}.png"
    tampered_path = OUT / f"synthetic_mrz_passport_tampered_{DOC_NUMBER}.png"
    render(tampered=False).save(genuine_path)
    render(tampered=True).save(tampered_path)
    line1, line2 = build_mrz()
    print("MRZ line1:", line1)
    print("MRZ line2:", line2)
    print("Wrote:", genuine_path.name)
    print("Wrote:", tampered_path.name)


if __name__ == "__main__":
    main()

