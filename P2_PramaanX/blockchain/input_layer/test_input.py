import os
from input_integrity import (
    create_input_record_from_file,
    verify_input_hash,
    read_file_bytes,
    prepare_input_for_blockchain,
    export_input_record
)


# ------------------------------------------------
# CONFIGURATION
# ------------------------------------------------

verification_id = "PX001"
file_path = "blockchain/input_layer/test_documents/synthetic_passport_input_DEMO-PAS-001.png"


# ------------------------------------------------
# STEP 1: Read and validate the ORIGINAL document
# ------------------------------------------------

original_bytes = read_file_bytes(file_path)


# ------------------------------------------------
# STEP 2: Create the INPUT record and generate H1
# ------------------------------------------------

record = create_input_record_from_file(
    verification_id,
    file_path
)

stored_h1 = record["record_hash"]


print("\n========== ORIGINAL DOCUMENT ==========")
print("Verification ID :", record["verification_id"])
print("Record Type     :", record["record_type"])
print("H1              :", stored_h1)
print("Previous Hash   :", record["previous_hash"])


# ------------------------------------------------
# STEP 3: Verify the ORIGINAL document
# ------------------------------------------------

original_result = verify_input_hash(
    verification_id,
    original_bytes,
    stored_h1
)

print("\n========== ORIGINAL VERIFICATION ==========")

if original_result:
    print("Status: MATCH")
else:
    print("Status: MISMATCH")


# ------------------------------------------------
# STEP 4: Simulate document modification
# ------------------------------------------------

modified_bytes = original_bytes + b" MODIFIED"


# ------------------------------------------------
# STEP 5: Verify MODIFIED document
# ------------------------------------------------

modified_result = verify_input_hash(
    verification_id,
    modified_bytes,
    stored_h1
)

print("\n========== MODIFIED VERIFICATION ==========")

if modified_result:
    print("Status: MATCH")
else:
    print("Status: MISMATCH")


# ------------------------------------------------
# STEP 6: Prepare P1 blockchain record
# ------------------------------------------------

print("\n========== P1 BLOCKCHAIN INPUT ==========")

blockchain_record = prepare_input_for_blockchain(
    verification_id,
    file_path
)


# ------------------------------------------------
# STEP 7: Create JSON record
# ------------------------------------------------

output_file = export_input_record(
    blockchain_record
)

print("\n========== JSON OUTPUT ==========")
print("Saved to:", output_file)

print("Verification ID :", blockchain_record["verification_id"])
print("Record Type     :", blockchain_record["record_type"])
print("Record Hash H1  :", blockchain_record["record_hash"])
print("Previous Hash   :", blockchain_record["previous_hash"])


# ------------------------------------------------
# STEP 8: Final P2 status
# ------------------------------------------------

print("\n========== P2 STATUS ==========")

if original_result and not modified_result:
    print("P2 INPUT INTEGRITY TEST: PASS")
else:
    print("P2 INPUT INTEGRITY TEST: FAIL")