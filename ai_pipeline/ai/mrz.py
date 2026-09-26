import re


MRZ_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"


def clean_mrz_line(line):
    line = line.upper()
    line = line.replace(" ", "")
    line = re.sub(r"[^A-Z0-9<]", "", line)

    return line


def find_mrz_lines(text):
    lines = text.splitlines()

    candidates = []

    for line in lines:
        cleaned = clean_mrz_line(line)

        if len(cleaned) >= 40:
            candidates.append(cleaned)

    return candidates


def char_value(char):
    if char == "<":
        return 0

    if char.isdigit():
        return int(char)

    return ord(char) - ord("A") + 10


def calculate_check_digit(value):
    weights = [7, 3, 1]

    total = 0

    for i, char in enumerate(value):
        total += char_value(char) * weights[i % 3]

    return str(total % 10)


def validate_check_digit(value, check_digit):
    if not check_digit.isdigit():
        return False

    return calculate_check_digit(value) == check_digit


def parse_td3(line1, line2):
    line1 = clean_mrz_line(line1)
    line2 = clean_mrz_line(line2)

    if len(line1) < 44 or len(line2) < 44:
        return {
            "valid_format": False,
            "error": "MRZ lines must be 44 characters"
        }

    document_type = line1[0:2]
    country = line1[2:5]

    name_section = line1[5:44]

    names = name_section.split("<<")

    surname = names[0].replace("<", " ").strip()

    given_names = ""

    if len(names) > 1:
        given_names = names[1].replace("<", " ").strip()

    passport_number = line2[0:9]
    passport_check = line2[9]

    nationality = line2[10:13]

    dob = line2[13:19]
    dob_check = line2[19]

    sex = line2[20]

    expiry = line2[21:27]
    expiry_check = line2[27]

    return {
        "valid_format": True,
        "document_type": document_type,
        "country": country,
        "surname": surname,
        "given_names": given_names,
        "passport_number": passport_number,
        "passport_check_digit": passport_check,
        "nationality": nationality,
        "dob": dob,
        "dob_check_digit": dob_check,
        "sex": sex,
        "expiry": expiry,
        "expiry_check_digit": expiry_check
    }


def validate_td3(parsed, line2):
    passport_field = line2[0:9]
    passport_digit = line2[9]

    dob_field = line2[13:19]
    dob_digit = line2[19]

    expiry_field = line2[21:27]
    expiry_digit = line2[27]

    passport_valid = validate_check_digit(
        passport_field,
        passport_digit
    )

    dob_valid = validate_check_digit(
        dob_field,
        dob_digit
    )

    expiry_valid = validate_check_digit(
        expiry_field,
        expiry_digit
    )

    parsed["checks"] = {
        "passport_number": passport_valid,
        "dob": dob_valid,
        "expiry": expiry_valid
    }

    parsed["mrz_valid"] = (
        passport_valid
        and dob_valid
        and expiry_valid
    )

    return parsed


def run_mrz(image_path):
    import easyocr

    reader = easyocr.Reader(["en"], gpu=False)

    results = reader.readtext(
        image_path,
        detail=0
    )

    candidates = find_mrz_lines(
        "\n".join(results)
    )

    if len(candidates) < 2:
        return {
            "mrz_valid": False,
            "error": "MRZ not detected"
        }

    line1 = candidates[-2]
    line2 = candidates[-1]

    parsed = parse_td3(
        line1,
        line2
    )

    if not parsed.get("valid_format"):
        return parsed

    return validate_td3(
        parsed,
        line2
    )
