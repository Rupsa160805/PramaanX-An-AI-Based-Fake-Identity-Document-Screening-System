from input_integrity import (
    create_input_record_from_file,
    verify_input_hash,
    read_file_bytes,
    export_input_record
)


# ============================================================
# P2 — INPUT INTEGRITY LAYER DEMONSTRATION
# ============================================================

VERIFICATION_ID = "PX001"

# Trusted original document
ORIGINAL_FILE = (
    "blockchain/input_layer/test_documents/"
    "synthetic_passport_original_DEMO-PAS-001.png"
)

# Document being verified
UPLOADED_FILE = (
    "blockchain/input_layer/test_documents/"
    "synthetic_passport_input_DEMO-PAS-001.png"
)


print("\n")
print("=" * 60)
print("              PRAAMAANX - P2")
print("             INPUT INTEGRITY LAYER")
print("=" * 60)


# ============================================================
# STEP 1 — CREATE TRUSTED BASELINE
# ============================================================

print("\n[1] CREATING TRUSTED BASELINE")
print("-" * 60)

original_record = create_input_record_from_file(
    VERIFICATION_ID,
    ORIGINAL_FILE
)

trusted_h1 = original_record["record_hash"]

print("Verification ID :", original_record["verification_id"])
print("Record Type     :", original_record["record_type"])
print("Trusted H1      :", trusted_h1)
print("Previous Hash   :", original_record["previous_hash"])


# ============================================================
# STEP 2 — EXPORT INPUT RECORD
# ============================================================

print("\n[2] CREATING INPUT RECORD")
print("-" * 60)

output_file = export_input_record(
    original_record
)

print("Record saved to :", output_file)


# ============================================================
# STEP 3 — READ UPLOADED DOCUMENT
# ============================================================

print("\n[3] READING UPLOADED DOCUMENT")
print("-" * 60)

uploaded_bytes = read_file_bytes(
    UPLOADED_FILE
)

print("Uploaded file   :", UPLOADED_FILE)
print("File read       : SUCCESS")


# ============================================================
# STEP 4 — VERIFY UPLOADED DOCUMENT
# ============================================================

print("\n[4] VERIFYING DOCUMENT INTEGRITY")
print("-" * 60)

verification_result = verify_input_hash(
    VERIFICATION_ID,
    uploaded_bytes,
    trusted_h1
)


if verification_result:
    print("Result          : MATCH")
    print("Integrity       : VERIFIED")
    print("Message         : Uploaded document matches trusted baseline.")

else:
    print("Result          : MISMATCH")
    print("Integrity       : NOT VERIFIED")
    print("Message         : Uploaded document differs from trusted baseline.")


# ============================================================
# STEP 5 — FINAL P2 STATUS
# ============================================================

print("\n")
print("=" * 60)
print("                  P2 RESULT")
print("=" * 60)

if verification_result:
    print("P2 INPUT INTEGRITY : PASS")
else:
    print("P2 INPUT INTEGRITY : MISMATCH DETECTED")

print("=" * 60)