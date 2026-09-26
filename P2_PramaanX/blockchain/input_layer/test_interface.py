from input_integrity import process_input_document


verification_id = "PX002"

file_path = "test_documents/passport_test1.jpeg"


record = process_input_document(
    verification_id,
    file_path
)


print("\n========== P2 INPUT INTERFACE ==========")

print("Verification ID :", record["verification_id"])
print("Record Type     :", record["record_type"])
print("Record Hash H1  :", record["record_hash"])
print("Previous Hash   :", record["previous_hash"])