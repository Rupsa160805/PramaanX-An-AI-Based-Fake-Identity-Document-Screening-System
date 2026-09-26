from datetime import datetime


def normalize(value):
    if value is None:
        return ""

    return (
        str(value)
        .upper()
        .replace("<", "")
        .replace(" ", "")
        .strip()
    )


def compare_values(a, b):
    return normalize(a) == normalize(b)


def validate_date_format(date_value, formats=None):
    if not date_value:
        return False

    if formats is None:
        formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d/%m/%y",
            "%d-%m-%y"
        ]

    for fmt in formats:
        try:
            datetime.strptime(date_value, fmt)
            return True
        except ValueError:
            continue

    return False


def validate_fields(ocr_data, mrz_data):
    result = {
        "passport_match": False,
        "dob_match": False,
        "nationality_match": False,
        "expiry_valid": False,
        "mrz_valid": False
    }

    if not mrz_data:
        return result

    # Compare passport number
    result["passport_match"] = compare_values(
        ocr_data.get("passport_number"),
        mrz_data.get("passport_number")
    )

    # Compare nationality
    result["nationality_match"] = compare_values(
        ocr_data.get("nationality"),
        mrz_data.get("nationality")
    )

    # MRZ check-digit validation
    result["mrz_valid"] = mrz_data.get(
        "mrz_valid",
        False
    )

    # DOB comparison
    ocr_dob = normalize(
        ocr_data.get("dob")
    )

    mrz_dob = normalize(
        mrz_data.get("dob")
    )

    if ocr_dob and mrz_dob:
        result["dob_match"] = (
            ocr_dob == mrz_dob
        )

    # Expiry check
    expiry = mrz_data.get("expiry")

    if expiry and len(expiry) == 6:
        try:
            expiry_date = datetime.strptime(
                expiry,
                "%y%m%d"
            )

            result["expiry_valid"] = (
                expiry_date.date()
                >= datetime.now().date()
            )

        except ValueError:
            result["expiry_valid"] = False

    return result
