"""Chinese Remainder Theorem helpers for ESP32 sensor readings."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

MODULI: tuple[int, int, int] = (97, 101, 103)
MAX_VALUE: int = 97 * 101 * 103


def encode(value: int) -> dict[int, int]:
    """Encode an integer into residues for the ESP32 CRT moduli."""
    if not isinstance(value, int):
        raise ValueError("value must be an integer")
    if value < 0 or value >= MAX_VALUE:
        raise ValueError(f"value must be in range 0..{MAX_VALUE - 1}")
    return {modulus: value % modulus for modulus in MODULI}


def _normalise_residues(residues: Mapping[int, int] | Sequence[object]) -> dict[int, int]:
    if isinstance(residues, Mapping):
        items = residues.items()
    else:
        items = []
        for index, item in enumerate(residues):
            if item is None:
                continue
            if isinstance(item, Mapping):
                modulus = item.get("modulus", item.get("m"))
                residue = item.get("residue", item.get("r"))
            elif isinstance(item, Sequence) and not isinstance(item, (str, bytes)) and len(item) == 2:
                modulus, residue = item
            else:
                modulus, residue = MODULI[index], item
            items.append((modulus, residue))

    normalised: dict[int, int] = {}
    for modulus, residue in items:
        if modulus is None or residue is None:
            continue
        modulus = int(modulus)
        residue = int(residue)
        if modulus not in MODULI:
            raise ValueError(f"unsupported CRT modulus: {modulus}")
        if residue < 0 or residue >= modulus:
            raise ValueError(f"residue for modulus {modulus} must be in range 0..{modulus - 1}")
        normalised[modulus] = residue
    return normalised


def _mod_inverse(a: int, modulus: int) -> int:
    return pow(a, -1, modulus)


def decode(residues: Mapping[int, int] | Sequence[object]) -> int:
    """Decode a reading from any two or more distinct ESP32 CRT residues.

    With all three residues, the result is unique across the full ESP32 range.
    With two residues, the smallest non-negative solution for that residue pair is
    returned; this matches gateway reassembly for sensor values constrained below
    the product of the received moduli.
    """
    normalised = _normalise_residues(residues)
    if len(normalised) < 2:
        raise ValueError("at least two CRT residues are required")

    modulus_product = 1
    for modulus in normalised:
        modulus_product *= modulus

    value = 0
    for modulus, residue in normalised.items():
        partial = modulus_product // modulus
        value += residue * partial * _mod_inverse(partial, modulus)

    value %= modulus_product
    if value < 0 or value >= MAX_VALUE:
        raise ValueError(f"decoded value outside supported range 0..{MAX_VALUE - 1}")
    return value
