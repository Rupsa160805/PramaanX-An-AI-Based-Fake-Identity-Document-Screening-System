## 1. Responsibility

Person 3 is responsible for:

- Consuming the existing AI/tampering-analysis result.
- Receiving H1 from the INPUT layer.
- Creating the canonical ANALYSIS payload.
- Generating H2.
- Creating the ANALYSIS blockchain record.
- Verifying the ANALYSIS record.
- Independently testing the module using a mock blockchain.

This module does NOT perform AI tampering detection itself.

The existing PramaanX AI pipeline performs tampering detection.

---

# 2. Directory Structure

```text
analysis_layer/
│
├── analysis_hash.py
├── analysis_service.py
└── README.md