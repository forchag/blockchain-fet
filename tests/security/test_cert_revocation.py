from __future__ import annotations

import os
import shutil
import subprocess
import pytest

from tests.security.conftest import ROOT, blocked
from tests.security.role_model import Permission, Role


def test_revoked_certificate_or_role_is_denied(fabric):
    identity = os.getenv("HRBAC_REVOCATION_TEST_ID")
    if not identity:
        pytest.skip("HRBAC_REVOCATION_TEST_ID not set; skipping destructive live revocation workflow")
    if shutil.which("fabric-ca-client") is None:
        pytest.skip("fabric-ca-client is not installed; cannot perform live certificate revocation workflow")
    script = ROOT / "scripts" / "revoke-cert.sh"
    if not script.exists():
        pytest.skip("certificate revocation script is unavailable")

    proc = subprocess.run(["bash", str(script), identity, "cessationofoperation"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    if proc.returncode != 0:
        pytest.skip(f"certificate revocation workflow unavailable: {proc.stdout}\n{proc.stderr}")

    result = fabric.invoke("CheckAccess", identity, Permission.WRITE_SENSOR.value, "North", "", role=Role.SENSOR)
    assert blocked(result), result.combined_output


def test_crl_revoked_serial_is_denied_when_configured(fabric):
    serial = os.getenv("HRBAC_REVOKED_SERIAL_HEX")
    if not serial:
        pytest.skip("HRBAC_REVOKED_SERIAL_HEX not set; skipping serial-specific CRL assertion")
    result = fabric.invoke("CheckAccess", "sensor-1", Permission.WRITE_SENSOR.value, "North", "", role=Role.SENSOR)
    assert blocked(result), f"expected serial {serial} to be blocked: {result.combined_output}"
