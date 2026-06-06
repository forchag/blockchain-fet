#!/usr/bin/env python3
"""Build a sensor flash package for FarmMSP edge devices."""

import argparse
import binascii
import pathlib
import struct
import sys

MAGIC = 0xDEADBEEF
ZONE_BYTES = 8
RAW_ED25519_KEY_BYTES = 32


def fail(message: str) -> None:
    print(f"make_flash_package.py: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_file(path: pathlib.Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        fail(f"unable to read {path}: {exc}")


def extract_raw_ed25519_private_key(key_bytes: bytes) -> bytes:
    """Return the 32-byte Ed25519 seed from raw or PKCS#8 DER/PEM input."""
    if len(key_bytes) == RAW_ED25519_KEY_BYTES:
        return key_bytes

    if b"-----BEGIN" in key_bytes:
        lines = [line.strip() for line in key_bytes.splitlines() if b"-----" not in line]
        try:
            key_bytes = binascii.a2b_base64(b"".join(lines))
        except binascii.Error as exc:
            fail(f"invalid PEM private key: {exc}")

    marker = b"\x04\x20"
    marker_index = key_bytes.rfind(marker)
    if marker_index != -1 and len(key_bytes) >= marker_index + 2 + RAW_ED25519_KEY_BYTES:
        return key_bytes[marker_index + 2 : marker_index + 2 + RAW_ED25519_KEY_BYTES]

    fail("private key must be a 32-byte raw Ed25519 seed or an Ed25519 PKCS#8 PEM/DER key")


def encode_zone(zone: str) -> bytes:
    encoded = zone.encode("ascii", errors="strict")
    if not encoded:
        fail("zone must not be empty")
    if len(encoded) > ZONE_BYTES:
        fail(f"zone must fit in {ZONE_BYTES} ASCII bytes")
    return encoded.ljust(ZONE_BYTES, b"\x00")


def build_package(cert: bytes, raw_key: bytes, zone: str) -> bytes:
    if len(cert) > 0xFFFF:
        fail("certificate is too large for 2-byte length field")
    body = struct.pack(">IH", MAGIC, len(cert)) + cert + raw_key + encode_zone(zone)
    return body + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a FarmMSP sensor binary flash package")
    parser.add_argument("--cert", required=True, type=pathlib.Path, help="sensor certificate path")
    parser.add_argument("--key", required=True, type=pathlib.Path, help="Ed25519 private key path")
    parser.add_argument("--zone", required=True, choices=("North", "South", "East", "West"), help="sensor zone")
    parser.add_argument("--out", required=True, type=pathlib.Path, help="output package path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cert = read_file(args.cert)
    raw_key = extract_raw_ed25519_private_key(read_file(args.key))
    package = build_package(cert, raw_key, args.zone)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    try:
        args.out.write_bytes(package)
    except OSError as exc:
        fail(f"unable to write {args.out}: {exc}")
    print(f"wrote {args.out} ({len(package)} bytes)")


if __name__ == "__main__":
    main()
