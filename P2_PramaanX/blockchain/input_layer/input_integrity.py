import hashlib
import json
import os


ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".pdf"
}


def validate_file(file_path):
    """
    Validate that the file exists and has
    a supported document extension.
    """

    if not os.path.isfile(file_path):
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    extension = os.path.splitext(file_path)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}"
        )

    return True

def create_input_payload(verification_id, file_bytes):
    """
    Create the canonical INPUT record for PramaanX.
    """

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    payload = {
        "verification_id": verification_id,
        "record_type": "INPUT",
        "file_hash": file_hash
    }

    return payload


def calculate_input_hash(payload):
    """
    Generate H1 using canonical JSON serialization.
    """

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def create_input_record(verification_id, file_bytes):
    """
    Create the complete P2 INPUT record.
    """

    payload = create_input_payload(
        verification_id,
        file_bytes
    )

    h1 = calculate_input_hash(payload)

    return {
        "verification_id": verification_id,
        "record_type": "INPUT",
        "record_hash": h1,
        "previous_hash": ""
    }


def verify_input_hash(verification_id, file_bytes, stored_hash):
    """
    Recalculate the INPUT hash and compare it
    with the previously stored H1.
    """

    current_record = create_input_record(
        verification_id,
        file_bytes
    )

    current_hash = current_record["record_hash"]

    return current_hash == stored_hash
def get_blockchain_record(verification_id, file_bytes):
    """
    Create the INPUT record that will later
    be sent to the blockchain service.
    """

    record = create_input_record(
        verification_id,
        file_bytes
    )

    return {
        "verification_id": record["verification_id"],
        "record_type": record["record_type"],
        "record_hash": record["record_hash"],
        "previous_hash": record["previous_hash"]
    }
def read_file_bytes(file_path):
    """
    Read and validate the uploaded document
    as raw bytes.
    """

    validate_file(file_path)

    with open(file_path, "rb") as file:
        return file.read()
def create_input_record_from_file(verification_id, file_path):
    """
    Create the INPUT blockchain record
    from an actual uploaded document.
    """

    file_bytes = read_file_bytes(file_path)

    return create_input_record(
        verification_id,
        file_bytes
    )
def prepare_input_for_blockchain(verification_id, file_path):
    """
    Prepare the INPUT record for the shared
    blockchain service created by P1.
    """

    record = create_input_record_from_file(
        verification_id,
        file_path
    )

    return {
        "verification_id": record["verification_id"],
        "record_type": record["record_type"],
        "record_hash": record["record_hash"],
        "previous_hash": record["previous_hash"]
    }
def export_input_record(record, output_file="input_record.json"):
    """
    Save the P2 INPUT record as a JSON file.
    """

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(
            record,
            file,
            indent=4
        )

    return output_file
def process_input_document(verification_id, file_path):
    """
    Main P2 entry point.

    Reads a document, validates it, generates H1,
    and returns the INPUT record.
    """

    record = create_input_record_from_file(
        verification_id,
        file_path
    )

    return record