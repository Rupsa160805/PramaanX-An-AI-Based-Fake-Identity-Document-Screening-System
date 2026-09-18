# PramaanX synthetic upload cases

These files are synthetic UI test fixtures, not identity documents. They do
not represent real people, passports, national IDs, or government records.

Use the **Document screening** page and enter the document number shown below.

| File | Document number | Expected evidence outcome |
| --- | --- | --- |
| `synthetic_original_Q2714253.png` | `Q2714253` | Reference found, clean synthetic evidence, LOW risk |
| `synthetic_original_P8841207.png` | `P8841207` | Reference found, clean synthetic evidence, LOW risk |
| `synthetic_tampered_unknown_X9000001.png` | `X9000001` | Reference missing plus tamper/MRZ flags, HIGH risk |
| `synthetic_tampered_known_Q2714253.png` | `Q2714253` | Reference found but tamper/MRZ flags, MEDIUM risk |
| `synthetic_passport_original_DEMO-PAS-001.png` | `DEMO-PAS-001` | Passport-style synthetic reference, LOW risk |
| `synthetic_passport_tampered_DEMO-PAS-001.png` | `DEMO-PAS-001` | Passport-style tamper flags, MEDIUM risk |
| `synthetic_aadhaar_original_DEMO-AAD-001.png` | `DEMO-AAD-001` | Aadhaar-style synthetic reference, LOW risk |
| `synthetic_aadhaar_tampered_DEMO-AAD-001.png` | `DEMO-AAD-001` | Aadhaar-style tamper flags, MEDIUM risk |
| `synthetic_aadhaar_tampered_unknown_AAD-FAKE-901.png` | `AAD-FAKE-901` | Unknown Aadhaar-style fake, HIGH risk |

The result is an explainable prototype risk assessment for an authorized
officer, not a legal authenticity verdict. The clean/tampered behavior is
provided by the explicitly configured `demo_document_pipeline` marker and
must be replaced by the real OCR/MRZ/tampering pipeline for production use.

The seeded demo login is:

`demo.officer@pramaanx.local` / `Demo@12345`
