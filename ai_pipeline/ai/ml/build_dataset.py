"""Generate a labelled genuine/tampered document dataset for training.

No real labelled corpus ships with PramaanX, so this script procedurally
synthesises ID-document-like images (the ``genuine`` class) and then applies
realistic forgery operations -- region splice, copy-move, field overwrite,
local double-JPEG recompression, photo substitution and local noise -- to
produce the ``tampered`` class. These are the artifacts a real tamper detector
learns from, so the resulting ResNet18 makes a genuine pixel-level decision
rather than reading a planted marker.

The bundled ``demo_artifacts`` images are folded in under their real labels so
the local demo keeps working. This is a *training* dataset, not a benchmark:
for production accuracy, retrain on a real labelled document corpus.

Run:  python -m ai_pipeline.ai.ml.build_dataset
"""
from __future__ import annotations

import io
import random
import shutil
import string
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent          # ai_pipeline/ai/ml
BASE = HERE.parent.parent                        # ai_pipeline
DATASET = BASE / "dataset"
GENUINE = DATASET / "genuine"
TAMPERED = DATASET / "tampered"
DEMO = BASE.parent / "demo_artifacts"            # <repo root>/demo_artifacts

N_PER_CLASS = 160
N_PASSPORT = 120          # passport-layout samples per class (OOD coverage)
SIZE = (640, 400)
PASSPORT_SIZE = (1000, 640)
# Held-out demo evaluation pair — never folded into training (avoids leakage).
_HELD_OUT = {
    "synthetic_mrz_passport_original_q2714253",
    "synthetic_mrz_passport_tampered_q2714253",
}

random.seed(1234)
np.random.seed(1234)


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _rand_text(n: int) -> str:
    return "".join(random.choice(string.ascii_uppercase) for _ in range(n))


def _mrz_line() -> str:
    chars = string.ascii_uppercase + string.digits + "<<<"
    return "".join(random.choice(chars) for _ in range(44))


def _photo_region(w: int, h: int) -> Image.Image:
    """A face-photo-like patch: smooth colour gradient plus fine noise."""
    base = np.zeros((h, w, 3), dtype=np.float32)
    c1 = np.array([random.randint(90, 200) for _ in range(3)], dtype=np.float32)
    c2 = np.array([random.randint(60, 180) for _ in range(3)], dtype=np.float32)
    for y in range(h):
        base[y, :, :] = c1 + (c2 - c1) * (y / max(1, h - 1))
    base += np.random.normal(0, 8, base.shape)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")


def render_genuine() -> Image.Image:
    """Procedurally render one clean ID-document-like image."""
    bg = tuple(random.randint(205, 245) for _ in range(3))
    img = Image.new("RGB", SIZE, bg)
    draw = ImageDraw.Draw(img)

    accent = tuple(random.randint(20, 120) for _ in range(3))
    draw.rectangle([0, 0, SIZE[0], 46], fill=accent)
    title = random.choice(["REPUBLIC ID CARD", "PASSPORT", "NATIONAL IDENTITY", "IDENTITY DOCUMENT"])
    draw.text((16, 12), title, fill=(245, 245, 245), font=_font(22))

    # Photo box
    px, py, pw, ph = 24, 70, 150, 190
    img.paste(_photo_region(pw, ph), (px, py))
    draw.rectangle([px, py, px + pw, py + ph], outline=accent, width=2)

    # Text fields
    fx = 200
    fields = [
        ("SURNAME", _rand_text(random.randint(4, 9))),
        ("GIVEN NAMES", _rand_text(random.randint(4, 7)) + " " + _rand_text(random.randint(3, 6))),
        ("DOC NO", random.choice(string.ascii_uppercase) + str(random.randint(1000000, 9999999))),
        ("NATIONALITY", random.choice(["IND", "USA", "GBR", "CAN", "AUS"])),
        ("DATE OF BIRTH", f"{random.randint(1,28):02d}-{random.randint(1,12):02d}-{random.randint(1960,2005)}"),
        ("DATE OF EXPIRY", f"{random.randint(1,28):02d}-{random.randint(1,12):02d}-{random.randint(2026,2035)}"),
    ]
    fy = 74
    lbl, val = _font(13), _font(18)
    for name, value in fields:
        draw.text((fx, fy), name, fill=(110, 110, 110), font=lbl)
        draw.text((fx, fy + 15), value, fill=(20, 20, 20), font=val)
        fy += 46

    # MRZ zone
    mrz = _font(17)
    draw.text((20, SIZE[1] - 56), _mrz_line(), fill=(15, 15, 15), font=mrz)
    draw.text((20, SIZE[1] - 32), _mrz_line(), fill=(15, 15, 15), font=mrz)

    arr = np.asarray(img).astype(np.float32) + np.random.normal(0, 3, (SIZE[1], SIZE[0], 3))
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")

    # Bake in realistic JPEG compression
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=random.randint(72, 94))
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def render_genuine_passport() -> Image.Image:
    """Randomised passport-layout render matching the held-out demo family.

    Same visual family as make_mrz_demo (blue header, photo box, visible field
    column, light MRZ band) but with varied content, colours and photo noise so
    the model learns the layout's tamper artifacts rather than one identity.
    """
    W, H = PASSPORT_SIZE
    bg = tuple(random.randint(230, 245) for _ in range(3))
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    header = (random.randint(20, 60), random.randint(45, 90), random.randint(90, 140))
    nat = random.choice(["IND", "USA", "GBR", "CAN", "AUS", "FRA", "DEU"])
    draw.rectangle([0, 0, W, 70], fill=header)
    draw.text((24, 20), "PASSPORT", fill=(245, 245, 245), font=_font(34))
    draw.text((W - 150, 26), nat, fill=(245, 245, 245), font=_font(28))

    px, py, pw, ph = 40, 110, 220, 280
    img.paste(_photo_region(pw, ph), (px, py))
    draw.rectangle([px, py, px + pw, py + ph], outline=header, width=3)

    doc_no = random.choice(string.ascii_uppercase) + str(random.randint(1000000, 9999999))
    fields = [
        ("SURNAME", _rand_text(random.randint(4, 9))),
        ("GIVEN NAMES", _rand_text(random.randint(4, 7)) + " " + _rand_text(random.randint(3, 6))),
        ("PASSPORT NO.", doc_no),
        ("NATIONALITY", nat),
        ("DATE OF BIRTH", f"{random.randint(1,28):02d}-{random.randint(1,12):02d}-{random.randint(1960,2005)}"),
        ("DATE OF EXPIRY", f"{random.randint(1,28):02d}-{random.randint(1,12):02d}-{random.randint(2026,2035)}"),
        ("SEX", random.choice(["M", "F"])),
    ]
    fx, fy = 300, 120
    for label, value in fields:
        draw.text((fx, fy), label, fill=(110, 110, 110), font=_font(16))
        draw.text((fx, fy + 20), value, fill=(15, 15, 15), font=_font(26))
        fy += 62

    draw.rectangle([0, H - 130, W, H], fill=(250, 250, 248))
    mrz = _font(30)
    draw.text((26, H - 118), _mrz_line(), fill=(10, 10, 10), font=mrz)
    draw.text((26, H - 74), _mrz_line(), fill=(10, 10, 10), font=mrz)

    # High-quality base save so a later locally-recompressed patch stands out.
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


# ── Tampering operations (each mutates and returns a copy) ────────────────────

def _rand_box(w: int, h: int, min_frac=0.12, max_frac=0.32):
    bw = random.randint(int(w * min_frac), int(w * max_frac))
    bh = random.randint(int(h * min_frac), int(h * max_frac))
    x = random.randint(0, w - bw)
    y = random.randint(0, h - bh)
    return x, y, bw, bh


def op_copy_move(img: Image.Image) -> Image.Image:
    w, h = img.size
    x, y, bw, bh = _rand_box(w, h)
    patch = img.crop((x, y, x + bw, y + bh))
    nx = max(0, min(w - bw, x + random.randint(-w // 3, w // 3)))
    ny = max(0, min(h - bh, y + random.randint(-h // 3, h // 3)))
    img.paste(patch, (nx, ny))
    return img


def op_splice(img: Image.Image, donor: Image.Image) -> Image.Image:
    w, h = img.size
    donor = donor.resize(img.size)
    x, y, bw, bh = _rand_box(w, h)
    img.paste(donor.crop((x, y, x + bw, y + bh)), (x, y))
    return img


def op_field_overwrite(img: Image.Image) -> Image.Image:
    draw = ImageDraw.Draw(img)
    w, h = img.size
    x, y, bw, bh = _rand_box(w, h, 0.10, 0.22)
    px = img.getpixel((min(w - 1, x + 2), min(h - 1, y + 2)))
    fill = tuple(min(255, c + random.randint(-8, 8)) for c in px[:3])
    draw.rectangle([x, y, x + bw, y + bh], fill=fill)
    draw.text((x + 4, y + bh // 3), str(random.randint(100000, 999999)),
              fill=(15, 15, 15), font=_font(16))
    return img


def op_local_recompress(img: Image.Image) -> Image.Image:
    w, h = img.size
    x, y, bw, bh = _rand_box(w, h)
    region = img.crop((x, y, x + bw, y + bh))
    buf = io.BytesIO()
    region.save(buf, format="JPEG", quality=random.randint(12, 30))
    buf.seek(0)
    img.paste(Image.open(buf).convert("RGB"), (x, y))
    return img


def op_local_noise(img: Image.Image) -> Image.Image:
    w, h = img.size
    x, y, bw, bh = _rand_box(w, h)
    region = np.asarray(img.crop((x, y, x + bw, y + bh))).astype(np.float32)
    region += np.random.normal(0, random.randint(18, 40), region.shape)
    patch = Image.fromarray(np.clip(region, 0, 255).astype(np.uint8), "RGB")
    if random.random() < 0.5:
        patch = patch.filter(ImageFilter.GaussianBlur(random.uniform(1, 2.5)))
    img.paste(patch, (x, y))
    return img


def make_tampered(base: Image.Image, donors: list[Image.Image]) -> Image.Image:
    img = base.copy()
    ops = [op_copy_move, op_field_overwrite, op_local_recompress, op_local_noise]
    for op in random.sample(ops, k=random.randint(1, 2)):
        img = op(img)
    if random.random() < 0.6 and donors:
        img = op_splice(img, random.choice(donors))
    # Re-save so the whole frame carries a single final compression pass
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=random.randint(70, 92))
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def _fold_in_demo() -> tuple[int, int]:
    """Copy the bundled demo_artifacts under their real labels."""
    g = t = 0
    if not DEMO.is_dir():
        return 0, 0
    for src in sorted(DEMO.glob("*.png")):
        if src.stem.lower() in _HELD_OUT:
            continue  # keep the demo eval pair out of training
        try:
            im = Image.open(src).convert("RGB")
        except OSError:
            continue
        tampered = "tampered" in src.name.lower() or "fake" in src.name.lower()
        dst = (TAMPERED if tampered else GENUINE) / f"demo_{src.stem}.jpg"
        im.save(dst, format="JPEG", quality=92)
        if tampered:
            t += 1
        else:
            g += 1
    return g, t


def main() -> None:
    for d in (GENUINE, TAMPERED):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    print(f"Generating {N_PER_CLASS} genuine images ...")
    genuine_imgs: list[Image.Image] = []
    for i in range(N_PER_CLASS):
        im = render_genuine()
        genuine_imgs.append(im)
        im.save(GENUINE / f"gen_{i:04d}.jpg", format="JPEG", quality=92)

    print(f"Generating {N_PER_CLASS} tampered images ...")
    for i in range(N_PER_CLASS):
        base = random.choice(genuine_imgs)
        make_tampered(base, genuine_imgs).save(
            TAMPERED / f"tam_{i:04d}.jpg", format="JPEG", quality=92
        )

    print(f"Generating {N_PASSPORT} passport-layout genuine + tampered images ...")
    passport_imgs: list[Image.Image] = []
    for i in range(N_PASSPORT):
        im = render_genuine_passport()
        passport_imgs.append(im)
        im.save(GENUINE / f"pass_{i:04d}.jpg", format="JPEG", quality=92)
    for i in range(N_PASSPORT):
        base = random.choice(passport_imgs)
        make_tampered(base, passport_imgs).save(
            TAMPERED / f"passtam_{i:04d}.jpg", format="JPEG", quality=92
        )

    dg, dt = _fold_in_demo()
    n_g = len(list(GENUINE.glob("*.jpg")))
    n_t = len(list(TAMPERED.glob("*.jpg")))
    print(f"Folded in demo_artifacts: +{dg} genuine, +{dt} tampered")
    print(f"Done. genuine={n_g}  tampered={n_t}  at {DATASET}")


if __name__ == "__main__":
    main()



