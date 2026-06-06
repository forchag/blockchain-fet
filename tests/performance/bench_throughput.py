#!/usr/bin/env python3
"""Throughput benchmark for the live HRBAC Fabric network."""

from __future__ import annotations

import argparse
import csv
import math
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.performance.workload_generator import OperationType, WorkloadGenerator, validate_distribution

LEVELS = (10, 20, 30, 40, 50, 60, 70, 80, 90, 100)
REPEATS = 5
DURATION_SECONDS = 60
RESULTS = ROOT / "results" / "throughput.csv"


@dataclass(frozen=True)
class PeerConfig:
    channel: str = os.getenv("CHANNEL_NAME", os.getenv("HRBAC_CHANNEL", "farmchannel"))
    chaincode: str = os.getenv("CHAINCODE_NAME", os.getenv("HRBAC_CHAINCODE", "hrbac"))
    orderer: str = os.getenv("ORDERER_ADDRESS", os.getenv("HRBAC_ORDERER", "localhost:7050"))
    orderer_hostname: str = os.getenv("ORDERER_TLS_HOSTNAME", "orderer0.farm.tn")
    orderer_ca: str = os.getenv("ORDERER_TLS_CA", str(ROOT / "network/crypto-config/ordererOrganizations/farm.tn/orderers/orderer0.farm.tn/tls/ca.crt"))
    timeout: int = int(os.getenv("HRBAC_PEER_TIMEOUT", "30"))


def role_env(role: str) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CORE_PEER_LOCALMSPID", "FarmMSP")
    env.setdefault("CORE_PEER_ADDRESS", "localhost:7051")
    env.setdefault("CORE_PEER_TLS_ENABLED", "true")
    env.setdefault("CORE_PEER_MSPCONFIGPATH", str(ROOT / "network/crypto-config/peerOrganizations/farm.tn/users/Admin@farm.tn/msp"))
    env.setdefault("CORE_PEER_TLS_ROOTCERT_FILE", str(ROOT / "network/crypto-config/peerOrganizations/farm.tn/peers/peer0.north.farm.tn/tls/ca.crt"))
    key = role.upper().replace(" ", "_")
    if msp := os.getenv(f"HRBAC_IDENTITY_{key}_MSP"):
        env["CORE_PEER_MSPCONFIGPATH"] = msp
    if cert := os.getenv(f"HRBAC_IDENTITY_{key}_TLS_ROOTCERT_FILE"):
        env["CORE_PEER_TLS_ROOTCERT_FILE"] = cert
    if address := os.getenv(f"HRBAC_IDENTITY_{key}_PEER_ADDRESS"):
        env["CORE_PEER_ADDRESS"] = address
    return env


def invoke(config: PeerConfig, operation) -> bool:
    args = [operation.transaction, *operation.args]
    if operation.requires_nonce:
        args.append(f"bench-{uuid.uuid4()}")
    import json

    payload = json.dumps({"Args": args}, separators=(",", ":"))
    cmd = ["peer", "chaincode", "invoke", "-C", config.channel, "-n", config.chaincode, "-o", config.orderer, "--ordererTLSHostnameOverride", config.orderer_hostname, "--tls", "--cafile", config.orderer_ca, "-c", payload]
    proc = subprocess.run(cmd, env=role_env(operation.role), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=config.timeout)
    return proc.returncode == 0


def run_once(level: int, duration: int, seed: int) -> tuple[float, int, int]:
    config = PeerConfig()
    generator = WorkloadGenerator(seed=seed)
    stop = threading.Event()
    lock = threading.Lock()
    success = 0
    failure = 0

    def worker() -> None:
        nonlocal success, failure
        while not stop.is_set():
            try:
                ok = invoke(config, generator.next_operation())
            except Exception:
                ok = False
            with lock:
                if ok:
                    success += 1
                else:
                    failure += 1

    with ThreadPoolExecutor(max_workers=level) as executor:
        futures = [executor.submit(worker) for _ in range(level)]
        time.sleep(duration)
        stop.set()
        for future in futures:
            future.result()
    return success / duration, success, failure


def confidence_interval_95(values: list[float]) -> tuple[float, float]:
    avg = mean(values)
    if len(values) < 2:
        return avg, 0.0
    half_width = 1.96 * stdev(values) / math.sqrt(len(values))
    return avg, half_width


def dry_run(output: Path) -> None:
    observed = validate_distribution(lambda: WorkloadGenerator(seed=42))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["mode", "sensor_write_ratio", "query_ratio", "admin_ratio", "levels", "repeats", "duration_seconds"])
        writer.writeheader()
        writer.writerow({"mode": "dry-run", "sensor_write_ratio": f"{observed[OperationType.SENSOR_WRITE]:.4f}", "query_ratio": f"{observed[OperationType.QUERY]:.4f}", "admin_ratio": f"{observed[OperationType.ADMIN]:.4f}", "levels": " ".join(map(str, LEVELS)), "repeats": REPEATS, "duration_seconds": DURATION_SECONDS})
    print(f"dry-run ok: wrote configuration validation to {output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="validate workload/configuration without invoking Fabric")
    parser.add_argument("--output", type=Path, default=RESULTS)
    parser.add_argument("--duration", type=int, default=DURATION_SECONDS)
    parser.add_argument("--repeats", type=int, default=REPEATS)
    args = parser.parse_args()
    if args.dry_run:
        dry_run(args.output)
        return 0
    if shutil.which("peer") is None:
        print("peer CLI is required for live benchmarks", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for level in LEVELS:
        rates = []
        for repeat in range(1, args.repeats + 1):
            tps, success, failure = run_once(level, args.duration, seed=level * 100 + repeat)
            rates.append(tps)
            rows.append({"concurrency": level, "repeat": repeat, "duration_seconds": args.duration, "success": success, "failure": failure, "tps": f"{tps:.4f}", "mean_tps": "", "ci95_half_width": ""})
        avg, ci = confidence_interval_95(rates)
        rows.append({"concurrency": level, "repeat": "summary", "duration_seconds": args.duration, "success": "", "failure": "", "tps": "", "mean_tps": f"{avg:.4f}", "ci95_half_width": f"{ci:.4f}"})
        if level == 50 and not (49.5 <= avg <= 77.0):
            print(f"warning: 50-client TPS {avg:.2f} outside expected hardware-tolerant range 49.5-77.0", file=sys.stderr)
    with args.output.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
