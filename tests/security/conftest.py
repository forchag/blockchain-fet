"""Pytest fixtures for live HRBAC Fabric security tests.

The tests in this package intentionally exercise a running Fabric network.  If
that network (or the Fabric CLI) is not available, collection succeeds and the
suite is skipped with a clear reason instead of failing during import.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.security.role_model import ROLE_ZONES, Role  # noqa: E402


DEFAULT_ENV = {
    "CORE_PEER_LOCALMSPID": "FarmMSP",
    "CORE_PEER_ADDRESS": "localhost:7051",
    "CORE_PEER_TLS_ENABLED": "true",
    "CORE_PEER_MSPCONFIGPATH": str(ROOT / "network/crypto-config/peerOrganizations/farm.tn/users/Admin@farm.tn/msp"),
    "CORE_PEER_TLS_ROOTCERT_FILE": str(ROOT / "network/crypto-config/peerOrganizations/farm.tn/peers/peer0.north.farm.tn/tls/ca.crt"),
}


@dataclass(frozen=True)
class FabricResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int
    elapsed_ms: float

    @property
    def combined_output(self) -> str:
        return "\n".join(part for part in (self.stdout, self.stderr) if part)


class FabricCLI:
    def __init__(self) -> None:
        self.channel = os.getenv("CHANNEL_NAME", os.getenv("HRBAC_CHANNEL", "farmchannel"))
        self.chaincode = os.getenv("CHAINCODE_NAME", os.getenv("HRBAC_CHAINCODE", "hrbac"))
        self.orderer = os.getenv("ORDERER_ADDRESS", os.getenv("HRBAC_ORDERER", "localhost:7050"))
        self.orderer_hostname = os.getenv("ORDERER_TLS_HOSTNAME", "orderer0.farm.tn")
        self.orderer_ca = os.getenv(
            "ORDERER_TLS_CA",
            str(ROOT / "network/crypto-config/ordererOrganizations/farm.tn/orderers/orderer0.farm.tn/tls/ca.crt"),
        )
        self.base_env = os.environ.copy()
        self.base_env.update({key: os.getenv(key, value) for key, value in DEFAULT_ENV.items()})
        self.timeout = int(os.getenv("HRBAC_PEER_TIMEOUT", "30"))

    def identity_available(self, role: Role) -> bool:
        if role is Role.ADMIN:
            return True
        role_key = role.value.upper().replace(" ", "_")
        configured = os.getenv(f"HRBAC_IDENTITY_{role_key}_MSP")
        return bool(configured and Path(configured).exists())

    def role_env(self, role: Role) -> dict[str, str]:
        env = self.base_env.copy()
        role_key = role.value.upper().replace(" ", "_")
        role_msp = os.getenv(f"HRBAC_IDENTITY_{role_key}_MSP")
        role_peer_address = os.getenv(f"HRBAC_IDENTITY_{role_key}_PEER_ADDRESS")
        role_tls_root = os.getenv(f"HRBAC_IDENTITY_{role_key}_TLS_ROOTCERT_FILE")
        if role_msp:
            env["CORE_PEER_MSPCONFIGPATH"] = role_msp
        if role_peer_address:
            env["CORE_PEER_ADDRESS"] = role_peer_address
        if role_tls_root:
            env["CORE_PEER_TLS_ROOTCERT_FILE"] = role_tls_root
        return env

    def invoke(self, function: str, *args: str, role: Role | None = None, nonce: str | None = None, timeout: int | None = None) -> FabricResult:
        call_args = [function, *map(str, args)]
        if nonce is not None:
            call_args.append(nonce)
        payload = json.dumps({"Args": call_args}, separators=(",", ":"))
        cmd = [
            "peer",
            "chaincode",
            "invoke",
            "-C",
            self.channel,
            "-n",
            self.chaincode,
            "-o",
            self.orderer,
            "--ordererTLSHostnameOverride",
            self.orderer_hostname,
            "--tls",
            "--cafile",
            self.orderer_ca,
            "-c",
            payload,
        ]
        return self._run(cmd, env=self.role_env(role) if role else self.base_env, timeout=timeout)

    def query(self, function: str, *args: str, role: Role | None = None, timeout: int | None = None) -> FabricResult:
        payload = json.dumps({"Args": [function, *map(str, args)]}, separators=(",", ":"))
        cmd = ["peer", "chaincode", "query", "-C", self.channel, "-n", self.chaincode, "-c", payload]
        return self._run(cmd, env=self.role_env(role) if role else self.base_env, timeout=timeout)

    def _run(self, cmd: list[str], *, env: dict[str, str], timeout: int | None = None) -> FabricResult:
        start = time.perf_counter()
        proc = subprocess.run(cmd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout or self.timeout)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return FabricResult(proc.returncode == 0, proc.stdout.strip(), proc.stderr.strip(), proc.returncode, elapsed_ms)

    def network_ready(self) -> tuple[bool, str]:
        if shutil.which("peer") is None:
            return False, "Fabric peer CLI is not installed or not on PATH"
        msp = self.base_env.get("CORE_PEER_MSPCONFIGPATH", "")
        if msp and not Path(msp).exists():
            return False, f"admin MSP path does not exist: {msp}"
        ca = Path(self.orderer_ca)
        if not ca.exists():
            return False, f"orderer TLS CA file does not exist: {ca}"
        cmd = ["peer", "lifecycle", "chaincode", "querycommitted", "--channelID", self.channel, "--name", self.chaincode]
        result = self._run(cmd, env=self.base_env, timeout=10)
        if not result.ok:
            return False, f"Fabric network/chaincode is unavailable: {result.combined_output or 'no output'}"
        return True, "ready"


@pytest.fixture(scope="session")
def fabric() -> FabricCLI:
    cli = FabricCLI()
    ready, reason = cli.network_ready()
    if not ready:
        pytest.skip(reason)
    return cli


@pytest.fixture(scope="session")
def expiry_iso() -> str:
    return (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture(scope="session", autouse=True)
def seed_roles(fabric: FabricCLI, expiry_iso: str) -> dict[Role, str]:
    seeded: dict[Role, str] = {}
    missing = [role.value for role in ROLE_ZONES if not fabric.identity_available(role)]
    if missing:
        pytest.skip("missing live Fabric MSP identities for roles: " + ", ".join(missing))
    for role, zones in ROLE_ZONES.items():
        subject = f"{role.value.lower()}-1"
        result = fabric.invoke("AssignRole", subject, role.value, zones, expiry_iso, role=Role.ADMIN, nonce=f"seed-{subject}-{uuid.uuid4()}")
        if not result.ok:
            pytest.skip(f"unable to seed {role.value} role for live security tests: {result.combined_output}")
        seeded[role] = subject
    return seeded


@pytest.fixture
def attempt_nonce() -> Iterable[str]:
    def make(prefix: str = "attempt") -> str:
        return f"{prefix}-{uuid.uuid4()}"

    return make


def extract_peer_payload(result: FabricResult) -> str:
    """Extract a chaincode payload from common peer CLI output shapes."""
    import re

    output = result.combined_output.strip()
    for pattern in (r'payload:"([^"]*)"', r'Payload: ([^\s]+)'):
        match = re.search(pattern, output)
        if match:
            return match.group(1)
    stripped = result.stdout.strip() or output
    return stripped.strip('"')


def blocked(result: FabricResult) -> bool:
    output = result.combined_output.lower()
    if not result.ok:
        return True
    return any(marker in output for marker in ("false", "denied", "unauthorized", "revoked", "replay"))
