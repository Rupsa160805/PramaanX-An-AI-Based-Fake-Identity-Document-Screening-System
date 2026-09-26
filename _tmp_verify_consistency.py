"""Ad-hoc live check: genuine vs tampered MRZ passport through /api/v1/verify."""
import json
import sys
from pathlib import Path

import requests

BASE = "http://127.0.0.1:5001"
KEY = "demo-secret-key"
ART = Path("demo_artifacts")

CASES = {
    "GENUINE": ART / "synthetic_mrz_passport_original_Q2714253.png",
    "TAMPERED": ART / "synthetic_mrz_passport_tampered_Q2714253.png",
}


def run(label: str, image: Path) -> None:
    with image.open("rb") as fh:
        resp = requests.post(
            f"{BASE}/api/v1/verify",
            headers={"X-API-Key": KEY},
            files={"document": (image.name, fh, "image/png")},
            data={"document_number": "Q2714253"},
            timeout=120,
        )
    print(f"===== {label} =====  HTTP {resp.status_code}")
    if resp.status_code != 200:
        print(resp.text[:400])
        return
    r = resp.json()
    ocr, mrz, tamp = r["ocr"], r["mrz"], r["tampering"]
    cons = r["consistency"]
    risk = r["risk"]
    print(f"ocr={ocr.get('status')} mrz={mrz.get('status')} valid={mrz.get('valid')}")
    print(f"tampering: detected={tamp.get('detected')} conf={tamp.get('confidence')}")
    print(f"consistency overall_match={cons.get('overall_match')}")
    for c in cons.get("checks", []):
        flag = "OK " if c["match"] else "MISMATCH"
        print(f"   [{flag}] {c['field']}: ocr={c['ocr_value']} mrz={c['mrz_value']}")
    print(f"risk score={risk['score']} level={risk['level']}")
    for reason in risk.get("reasons", []):
        print(f"   - {reason}")
    print()


if __name__ == "__main__":
    for label, image in CASES.items():
        if not image.exists():
            print(f"MISSING: {image}", file=sys.stderr)
            continue
        run(label, image)
