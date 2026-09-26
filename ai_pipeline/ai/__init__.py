"""
PramaanX AI Package
---------------------
Public interface for the AI layer.

Modules in this package were developed by the PramaanX AI team:
  preprocessing.py — image loading and enhancement (OpenCV)
  ocr.py           — EasyOCR field extraction
  mrz.py           — ICAO TD3 MRZ parsing and check-digit validation
  tampering.py     — ResNet18 tamper-detection classifier
  validation.py    — cross-field validation utilities

The pipeline orchestrator (pipeline.py) was developed by the backend team
and calls the above modules in sequence.
"""
