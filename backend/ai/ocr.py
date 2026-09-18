import easyocr
import re


# Create OCR reader once
reader = easyocr.Reader(["en"], gpu=False)


def read_text(image_path):
    results = reader.readtext(image_path, detail=1)

    output = []

    for item in results:
        bbox, text, confidence = item

        output.append({
            "text": text,
            "confidence": float(confidence),
            "bbox": bbox
        })

    return output


def get_all_text(image_path):
    results = read_text(image_path)

    text = " ".join(
        item["text"] for item in results
    )

    return text


def normalize_text(text):
    text = text.upper()
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_fields(image_path):
    results = read_text(image_path)

    all_text = " ".join(
        item["text"] for item in results
    )

    all_text = normalize_text(all_text)

    fields = {
        "name": None,
        "dob": None,
        "passport_number": None,
        "nationality": None,
        "expiry": None,
        "raw_text": all_text
    }

    # Passport number
    passport_match = re.search(
        r"\b[A-Z][0-9][A-Z0-9]{6}\b",
        all_text
    )

    if passport_match:
        fields["passport_number"] = passport_match.group()

    # Dates
    dates = re.findall(
        r"\b\d{2}[-/]\d{2}[-/]\d{4}\b",
        all_text
    )

    if len(dates) >= 1:
        fields["dob"] = dates[0]

    if len(dates) >= 2:
        fields["expiry"] = dates[-1]

    # Nationality
    nationality_match = re.search(
        r"\b(IND|USA|GBR|CAN|AUS|FRA|DEU|JPN)\b",
        all_text
    )

    if nationality_match:
        fields["nationality"] = nationality_match.group()

    return fields


def run_ocr(image_path):
    return extract_fields(image_path)
