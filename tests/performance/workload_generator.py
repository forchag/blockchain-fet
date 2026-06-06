"""Workload generation utilities for HRBAC performance benchmarks."""

from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Sequence


class OperationType(StrEnum):
    SENSOR_WRITE = "sensor_write"
    QUERY = "query"
    ADMIN = "admin"


@dataclass(frozen=True)
class WorkloadOperation:
    kind: OperationType
    transaction: str
    args: tuple[str, ...]
    role: str
    requires_nonce: bool = False


class WorkloadGenerator:
    """Generate HRBAC operations with the required 70/25/5 distribution."""

    def __init__(self, *, seed: int | None = None, zones: Sequence[str] = ("North", "South", "East", "West")) -> None:
        self.random = random.Random(seed)
        self.zones = tuple(zones)
        self.population = (OperationType.SENSOR_WRITE, OperationType.QUERY, OperationType.ADMIN)
        self.weights = (70, 25, 5)

    def next_operation(self) -> WorkloadOperation:
        kind = self.random.choices(self.population, weights=self.weights, k=1)[0]
        zone = self.random.choice(self.zones)
        suffix = uuid.uuid4().hex
        if kind is OperationType.SENSOR_WRITE:
            reading = json.dumps({"moisture": self.random.randint(1, 100), "temperature": round(self.random.uniform(5, 40), 2), "id": suffix})
            return WorkloadOperation(kind, "WriteSensorData", (f"sensor-{suffix}", reading, zone), "Sensor", True)
        if kind is OperationType.QUERY:
            role = self.random.choice(("Farmer", "Agronomist"))
            permission = "WriteSensor" if role == "Farmer" else "ControlZone"
            subject = f"{role.lower()}-1"
            return WorkloadOperation(kind, "CheckAccess", (subject, permission, zone, ""), role, False)
        # Low-frequency admin operation that exercises HRBAC without mutating roles.
        return WorkloadOperation(kind, "GetAuditLog", (), "Admin", False)

    def sample(self, count: int) -> list[WorkloadOperation]:
        return [self.next_operation() for _ in range(count)]


def validate_distribution(factory: Callable[[], WorkloadGenerator] = WorkloadGenerator, *, sample_size: int = 10_000, tolerance: float = 0.03) -> dict[OperationType, float]:
    generator = factory()
    counts = {kind: 0 for kind in OperationType}
    for operation in generator.sample(sample_size):
        counts[operation.kind] += 1
    observed = {kind: counts[kind] / sample_size for kind in OperationType}
    expected = {OperationType.SENSOR_WRITE: 0.70, OperationType.QUERY: 0.25, OperationType.ADMIN: 0.05}
    for kind, expected_ratio in expected.items():
        if abs(observed[kind] - expected_ratio) > tolerance:
            raise ValueError(f"{kind.value} distribution {observed[kind]:.3f} outside tolerance of {expected_ratio:.3f}")
    return observed
