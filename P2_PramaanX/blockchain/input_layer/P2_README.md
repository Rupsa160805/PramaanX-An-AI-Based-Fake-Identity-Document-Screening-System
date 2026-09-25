# PramaanX — P2 Input Integrity Layer

## 1. Overview

The **P2 Input Integrity Layer** is responsible for establishing and verifying the integrity of documents entering the PramaanX system.

P2 generates a cryptographic hash called **H1** from the document's bytes. This hash acts as a unique digital fingerprint of the document at the time it is processed.

Instead of storing the complete document in the blockchain layer, P2 prepares a lightweight **INPUT record** containing the document hash and related metadata.

---

## 2. Objective

The main objectives of P2 are:

* Validate the input document.
* Read the document as binary data.
* Generate a SHA-256 cryptographic hash (**H1**).
* Create an INPUT integrity record.
* Export the INPUT record as JSON.
* Verify a later document against a trusted baseline hash.
* Detect whether the uploaded document differs from the trusted baseline.
* Prepare structured data that can later be passed to the P1 blockchain layer.

---

## 3. P2 Workflow

The basic P2 workflow is:

```text
Document
   ↓
File Validation
   ↓
Read Document Bytes
   ↓
SHA-256 Hashing
   ↓
H1
   ↓
INPUT Record
   ↓
JSON / P1 Blockchain Handoff
```

### Integrity Verification Workflow

A trusted document is first processed to generate its baseline hash **H1**.

When another document is later uploaded for verification, P2 generates a new hash **H1'** and compares it with the trusted H1.

```text
Trusted Document
      ↓
     H1
      │
      │ compare
      ▼
Uploaded Document
      ↓
     H1'
      │
      ├── H1 = H1' → MATCH
      │
      └── H1 ≠ H1' → MISMATCH
```

### Meaning of the Result

**MATCH**

```text
H1 = H1'
```

The uploaded document has the same byte representation as the trusted baseline.

**MISMATCH**

```text
H1 ≠ H1'
```

The uploaded document differs from the trusted baseline.

A mismatch indicates an **integrity difference**. It does not, by itself, prove that the document is fraudulent.

---

## 4. Why SHA-256 Is Used

P2 uses **SHA-256** to generate the document hash.

A cryptographic hash converts the document's binary content into a fixed-length digital fingerprint.

For example:

```text
Document
   ↓
SHA-256
   ↓
H1
```

Even a small change in the document's bytes can result in a different hash.

Therefore:

```text
Same bytes
   ↓
Same hash
```

while:

```text
Different bytes
   ↓
Different hash
```

This allows P2 to perform efficient integrity verification without storing the entire document in the blockchain layer.

---

## 5. INPUT Record

P2 creates an INPUT record containing the document's integrity information.

Example:

```json
{
    "verification_id": "PX001",
    "record_type": "INPUT",
    "record_hash": "H1",
    "previous_hash": ""
}
```

### Fields

| Field             | Description                                          |
| ----------------- | ---------------------------------------------------- |
| `verification_id` | Unique identifier for the PramaanX verification case |
| `record_type`     | Identifies the record as an `INPUT` record           |
| `record_hash`     | SHA-256 hash (**H1**) generated from the document    |
| `previous_hash`   | Hash of the previous record when applicable          |

---

## 6. JSON Output

P2 exports the INPUT record into:

```text
input_record.json
```

The JSON file is a local development representation of the INPUT record.

Example:

```json
{
    "verification_id": "PX001",
    "record_type": "INPUT",
    "record_hash": "64-character-SHA256-hash",
    "previous_hash": ""
}
```

The actual document itself is **not stored inside this JSON record**.

---

## 7. Project Structure

The standalone P2 module is organized as follows:

```text
blockchain/
└── input_layer/
    │
    ├── input_integrity.py
    ├── demo_p2.py
    ├── input_record.json
    ├── README.md
    │
    └── test_documents/
        ├── synthetic_passport_original_DEMO-PAS-001.png
        └── synthetic_passport_input_DEMO-PAS-001.png
```

### File Description

#### `input_integrity.py`

The core P2 implementation.

It contains functionality for:

* file validation
* reading document bytes
* SHA-256 hash generation
* INPUT record creation
* hash verification
* JSON record generation

#### `demo_p2.py`

The standalone P2 demonstration script.

It demonstrates:

1. Creating a trusted baseline.
2. Generating H1.
3. Creating the INPUT record.
4. Exporting the JSON record.
5. Reading the uploaded document.
6. Comparing its hash with the trusted H1.
7. Returning MATCH or MISMATCH.

#### `input_record.json`

The generated JSON representation of the INPUT record.

#### `test_documents/`

Contains synthetic/dummy documents used for testing the P2 integrity mechanism.

---

## 8. Running P2

### From the project root

Run:

```powershell
python blockchain/input_layer/demo_p2.py
```

### From inside `blockchain/input_layer`

Run:

```powershell
python demo_p2.py
```

Make sure the document paths inside `demo_p2.py` correspond to the directory from which the script is being executed.

---

## 9. Test Case 1 — Identical Documents

For the first test, the trusted document and uploaded document should contain identical data.

```text
Trusted Document
      ↓
     H1

Uploaded Document
      ↓
     H1'

H1 = H1'
      ↓
   MATCH
```

Expected output:

```text
Result          : MATCH
Integrity       : VERIFIED

P2 INPUT INTEGRITY : PASS
```

This confirms that P2 correctly recognizes an unchanged document.

---

## 10. Test Case 2 — Modified Document

For the second test, modify the uploaded test document while keeping the trusted original unchanged.

```text
Trusted Document
      ↓
     H1

Modified Document
      ↓
     H1'

H1 ≠ H1'
      ↓
   MISMATCH
```

Expected output:

```text
Result          : MISMATCH
Integrity       : NOT VERIFIED

P2 INPUT INTEGRITY : MISMATCH DETECTED
```

This demonstrates that P2 detects a difference between the uploaded document and the trusted baseline.

---

## 11. Important Distinction: Integrity vs Authenticity

P2 is an **integrity verification layer**.

It answers:

> Does the uploaded document match the trusted digital representation?

It does not independently answer:

> Is this document genuinely issued by the claimed authority?

For example, if a completely altered document is uploaded to PramaanX for the first time and there is no trusted baseline H1, P2 cannot reconstruct the original document or determine what the original contents should have been.

Therefore, P2 requires a **trusted baseline** when performing historical integrity verification.

Document authenticity and content validation are handled through the other PramaanX components and trusted data sources.

---

## 12. Trusted Baseline Concept

The trusted baseline is important because hashing alone cannot tell us what the original document should have been.

The process is:

```text
Trusted Source / Previously Registered Document
                    ↓
                  H1
                    ↓
            Trusted Baseline
                    │
                    │
                    ▼
             Later Verification
                    │
                    ▼
             Uploaded Document
                    ↓
                   H1'
                    │
              ┌─────┴─────┐
              ↓           ↓
           H1 = H1'    H1 ≠ H1'
              ↓           ↓
            MATCH      MISMATCH
```

If no trusted baseline exists, P2 can still calculate a hash for the received document, but it cannot independently determine whether that document represents the legitimate original.

---

## 13. P1 Handoff

P2 is designed to work independently during development.

The generated INPUT record can later be passed to the P1 blockchain layer.

Conceptually:

```text
                P2
                 │
                 │ INPUT record
                 │
                 ▼
        ┌─────────────────┐
        │ verification_id │
        │ record_type     │
        │ record_hash H1  │
        │ previous_hash   │
        └─────────────────┘
                 │
                 ▼
                P1
                 │
                 ▼
            Blockchain
```

The current P2 implementation does **not** directly integrate with P1.

Integration will be performed after the independent P1, P2, P3, and P4 components are completed.

---

## 14. Privacy Principle

P2 does not need to place the complete document contents into the blockchain record.

Instead, it uses a cryptographic hash:

```text
Document
   ↓
SHA-256
   ↓
H1
```

The hash acts as a compact integrity fingerprint.

This helps separate:

```text
Document contents
```

from:

```text
Blockchain integrity record
```

---

## 15. Limitations

P2 has the following limitations:

1. A hash does not reveal the original document contents.
2. A hash cannot reconstruct an altered document.
3. A mismatch only indicates that the compared data differs.
4. P2 requires a trusted baseline for historical comparison.
5. P2 alone does not establish document authenticity.
6. P2 does not perform OCR, face verification, MRZ validation, or document-content analysis.
7. The current JSON file is a local development representation and is not the final blockchain storage mechanism.

---

## 16. Current Scope

P2 is currently implemented as an independent module.

The current implementation does not directly integrate with:

* PramaanX frontend
* Existing PramaanX backend
* P1 blockchain layer
* P3
* P4

The components will be integrated after each individual module is completed.

---

## 17. P2 Completion Criteria

P2 is considered complete when the following are working:

```text
✓ File validation
✓ Document byte reading
✓ SHA-256 H1 generation
✓ INPUT record creation
✓ Previous hash field
✓ JSON record generation
✓ Trusted baseline verification
✓ MATCH detection
✓ MISMATCH detection
✓ Real document comparison
✓ Standalone demonstration
✓ Documentation
```

---

## 18. Final P2 Flow

The complete standalone P2 flow is:

```text
                  DOCUMENT
                     │
                     ▼
              File Validation
                     │
                     ▼
              Read File Bytes
                     │
                     ▼
                SHA-256
                     │
                     ▼
                     H1
                     │
                     ▼
              INPUT RECORD
                     │
                     ▼
             input_record.json
                     │
                     │
          Trusted Baseline H1
                     │
                     ▼
             Later Verification
                     │
                     ▼
             Uploaded Document
                     │
                     ▼
                    H1'
                     │
              ┌──────┴──────┐
              │             │
           H1 = H1'      H1 ≠ H1'
              │             │
              ▼             ▼
            MATCH        MISMATCH
              │             │
              ▼             ▼
       Integrity OK    Difference Detected
```

---

## 19. P2 Status

**P2 — Input Integrity Layer**

**Status: Standalone implementation complete.**

The module is ready for final integration with the other PramaanX components after P1, P3, and P4 are completed.
