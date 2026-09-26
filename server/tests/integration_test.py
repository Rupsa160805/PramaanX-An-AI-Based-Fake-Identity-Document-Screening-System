"""Opt-in integration checks against P2's real API."""

from __future__ import annotations

import os

import pytest
import requests


P2_BASE_URL = os.getenv("P2_BASE_URL")
DOCUMENT_NUMBER = os.getenv("P4_INTEGRATION_DOCUMENT_NUMBER", "Q2714253")
LIVE_PHOTO_PATH = os.getenv("P4_INTEGRATION_LIVE_PHOTO_PATH")


@pytest.mark.skipif(
    not P2_BASE_URL or not LIVE_PHOTO_PATH,
    reason="set P2_BASE_URL and P4_INTEGRATION_LIVE_PHOTO_PATH",
)
def test_p2_can_reach_biometric_service():
    response = requests.get(f"{P2_BASE_URL.rstrip('/')}/api/health", timeout=10)
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


@pytest.mark.skipif(
    not P2_BASE_URL or not LIVE_PHOTO_PATH,
    reason="set P2_BASE_URL and P4_INTEGRATION_LIVE_PHOTO_PATH",
)
def test_p2_full_pipeline_returns_face_result():
    response = requests.post(
        f"{P2_BASE_URL.rstrip('/')}/api/analyze",
        json={"document_number": DOCUMENT_NUMBER, "live_photo_path": LIVE_PHOTO_PATH},
        timeout=60,
    )
    assert response.status_code < 500
    body = response.json()
    assert "face_verification" in body or "biometric" in body
