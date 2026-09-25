from input_integrity import (
    create_input_record_from_file,
    verify_input_hash,
    read_file_bytes,
    export_input_record
)


# ------------------------------------------------
# CONFIGURATION
# ------------------------------------------------

verification_id = "PX001"

original_file = "blockchain/input_layer/test_documents/synthetic_passport_original_DEMO-PAS-001.png"
uploaded_file = "blockchain/input_layer/test_documents/synthetic_passport_input_DEMO-PAS-001.png"


# ------------------------------------------------
# STEP 1: Create trusted baseline
# ------------------------------------------------

print("\n========== CREATE TRUSTED BASELINE ==========")

original_record = create_input_record_from_file(
    verification_id,
    original_file
)

original_h1 = original_record["record_hash"]

print("Verification ID :", verification_id)
print("Original H1     :", original_h1)


# ------------------------------------------------
# STEP 2: Save baseline record
# ------------------------------------------------

export_input_record(original_record)

print("\nTrusted INPUT record saved.")


# ------------------------------------------------
# STEP 3: Read uploaded document
# ------------------------------------------------

uploaded_bytes = read_file_bytes(uploaded_file)


# ------------------------------------------------
# STEP 4: Verify uploaded document
# ------------------------------------------------

print("\n========== UPLOADED DOCUMENT ==========")

result = verify_input_hash(
    verification_id,
    uploaded_bytes,
    original_h1
)


# ------------------------------------------------
# STEP 5: Display result
# ------------------------------------------------

print("\n========== VERIFICATION RESULT ==========")

if result:
    print("MATCH")
    print("Uploaded document matches the trusted baseline.")
else:
    print("MISMATCH")
    print("Uploaded document does NOT match the trusted baseline.")