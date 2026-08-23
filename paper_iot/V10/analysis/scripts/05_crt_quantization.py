#!/usr/bin/env python3
"""Phase 10: CRT recovery-bound and quantization recomputation.

Uses the exact deployed encoding in esp32/main/main.c and esp32/main/crt_encode.c
(moduli 97/101/103, packed = soil_raw*201 + temp_bucket, temp_bucket =
clip((temp_centi_c + 5500)/100, 0, 200)) applied to the released
engineering-unit columns in the field sensor-transaction trace.

Calibration gap (documented, not fabricated): the released repository
contains no calibration constant mapping the engineering-unit soil-moisture
percentage back to the firmware's 12-bit raw ADC count. We therefore report
the packed-value reconstruction under an explicitly stated linear assumption
(raw = round(pct/100 * 4095)) AND under its reversed-polarity counterpart
(raw = 4095 - round(pct/100 * 4095)), and show the headline finding --
100% of committed readings exceed the smallest two-residue recovery bound --
is invariant to which polarity is assumed, while the exact min/max packed
values are calibration-dependent and reported as such.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import FIELD_DIR, OUTPUTS_DIR, write_json

MODULI_DEPLOYED = [97, 101, 103]
MODULI_CORRECTED = [253, 254, 255]
TEMP_BUCKETS = 201

ST = pd.read_csv(FIELD_DIR / "sensor_transactions.csv")


def pairwise_bounds(moduli: list[int]) -> dict:
    a, b, c = moduli
    return {"a*b": a * b, "a*c": a * c, "b*c": b * c, "min": min(a * b, a * c, b * c),
            "max_triple_product": a * b * c}


def encode_packed(soil_raw: np.ndarray, temp_centi_c: np.ndarray) -> np.ndarray:
    soil = np.clip(soil_raw, 0, 4095).astype(np.int64)
    bucket = np.clip((temp_centi_c.astype(np.int64) + 5500) // 100, 0, TEMP_BUCKETS - 1)
    return soil * TEMP_BUCKETS + bucket


def reconstruct(polarity: str) -> dict:
    temp_centi = np.round(ST["temp_c"].values * 100).astype(np.int64)
    pct = ST["soil_moisture"].values
    if polarity == "direct":
        soil_raw = np.round(pct / 100.0 * 4095).astype(np.int64)
    else:
        soil_raw = np.round(4095 - pct / 100.0 * 4095).astype(np.int64)
    packed = encode_packed(soil_raw, temp_centi)
    bounds = pairwise_bounds(MODULI_DEPLOYED)
    exceed_min = int((packed >= bounds["min"]).sum())
    return {
        "polarity_assumption": polarity,
        "soil_raw_min": int(soil_raw.min()), "soil_raw_max": int(soil_raw.max()),
        "packed_min": int(packed.min()), "packed_max": int(packed.max()),
        "n_total": int(len(packed)),
        "n_exceed_min_bound": exceed_min,
        "pct_exceed_min_bound": float(exceed_min / len(packed) * 100),
    }


def corrected_domain() -> dict:
    """Corrected 8-bit soil encoding: quantise 12-bit raw to 8 bits, bound=253*254*255-min-pair? per V9.2:
    corrected legal domain max = 255*201+200 = 51455, moduli {253,254,255}."""
    a, b, c = MODULI_CORRECTED
    bounds = pairwise_bounds(MODULI_CORRECTED)
    legal_max = 255 * TEMP_BUCKETS + (TEMP_BUCKETS - 1)
    return {
        "moduli": MODULI_CORRECTED,
        "pairwise_bounds": bounds,
        "legal_domain_max": legal_max,
        "below_min_pairwise_bound": bool(legal_max < bounds["min"]),
    }


def quantization_error() -> dict:
    """Quantising the firmware's native 12-bit soil ADC range (0..4095) down
    to the corrected encoder's 8-bit soil field (0..255) by truncation
    (bucket = raw >> 4, i.e. keeping the most-significant 8 bits, the
    simplest and cheapest embedded-firmware quantisation), evaluated by an
    exhaustive sweep of the 12-bit domain -- not a theoretical half-step
    bound. We also report the round-to-nearest variant for comparison."""
    raw = np.arange(0, 4096)

    # Truncating quantiser: bucket = floor(raw / 16); reconstruction takes the
    # bucket's low edge, the natural behaviour of a bit-shift on firmware.
    bucket_trunc = raw // 16
    recon_trunc = bucket_trunc * 16
    err_trunc = np.abs(recon_trunc - raw) / 4095 * 100

    # Round-to-nearest quantiser, for comparison.
    bucket_round = np.round(raw / 4095 * 255)
    recon_round = bucket_round / 255 * 4095
    err_round = np.abs(recon_round - raw) / 4095 * 100

    return {
        "truncating_quantiser": {
            "max_error_pct_full_scale": float(err_trunc.max()),
            "rms_error_pct_full_scale": float(np.sqrt(np.mean(err_trunc ** 2))),
        },
        "round_to_nearest_quantiser": {
            "max_error_pct_full_scale": float(err_round.max()),
            "rms_error_pct_full_scale": float(np.sqrt(np.mean(err_round ** 2))),
        },
        "note": (
            "12-bit to 8-bit soil-field requantisation error, exhaustive sweep of the raw ADC "
            "domain (0..4095). The corrected firmware's bit-shift implementation corresponds to "
            "the truncating quantiser; round-to-nearest is shown for comparison only."
        ),
    }


def main() -> None:
    result = {
        "deployed_moduli": MODULI_DEPLOYED,
        "deployed_pairwise_bounds": pairwise_bounds(MODULI_DEPLOYED),
        "reconstruction_direct_polarity": reconstruct("direct"),
        "reconstruction_reversed_polarity": reconstruct("reversed"),
        "two_residue_reconstruction_count": int((ST["crt_residues_received"] == 2).sum()),
        "two_residue_reconstruction_pct": float((ST["crt_residues_received"] == 2).mean() * 100),
        "three_residue_count": int((ST["crt_residues_received"] == 3).sum()),
        "corrected_domain": corrected_domain(),
        "quantization_error": quantization_error(),
        "calibration_caveat": (
            "The released repository contains no ADC-to-percent calibration constant for "
            "soil_moisture (esp32/main/sensor.c transmits raw ADC counts only; no gateway or "
            "backend code in this repository converts them to a percentage). The percentage-to-raw "
            "mapping used here is an explicitly stated assumption, not a value taken from the "
            "codebase. The 100% bound-exceedance finding is invariant to the assumed polarity; the "
            "exact packed-value minimum and maximum are not."
        ),
    }
    write_json(OUTPUTS_DIR / "05_crt_quantization.json", result)


if __name__ == "__main__":
    main()
