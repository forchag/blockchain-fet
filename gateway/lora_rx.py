"""LoRa residue reception and CRT reassembly."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from crt_decode import MODULI, decode

DEFAULT_CHANNELS = (868.100, 868.300, 868.500)
ASSEMBLY_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class SensorReading:
    device_id: str
    reading_id: str
    value: int
    zone: str | None = None
    timestamp: float | None = None
    signature: str | bytes | None = None
    certificate: str | None = None
    residues: dict[int, int] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "reading_id": self.reading_id,
            "value": self.value,
            "zone": self.zone,
            "timestamp": self.timestamp,
            "signature": self.signature.hex() if isinstance(self.signature, bytes) else self.signature,
            "certificate": self.certificate,
            "residues": self.residues,
        }


@dataclass
class _Assembly:
    first_seen: float
    packets: list[dict[str, Any]] = field(default_factory=list)
    residues: dict[int, int] = field(default_factory=dict)


class LoRaReceiver:
    """Collect LoRa residue packets from three channels and assemble readings."""

    def __init__(
        self,
        channels: Iterable[float] = DEFAULT_CHANNELS,
        *,
        timeout_seconds: float = ASSEMBLY_TIMEOUT_SECONDS,
        packet_sources: Iterable[Callable[[], Any]] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.channels = tuple(channels)
        if len(self.channels) != 3:
            raise ValueError("LoRaReceiver must listen on exactly three channels")
        self.timeout_seconds = timeout_seconds
        self.packet_sources = tuple(packet_sources or ())
        self._clock = clock
        self._lock = threading.RLock()
        self._assemblies: dict[tuple[str, str], _Assembly] = {}
        self._assembled: set[tuple[str, str]] = set()
        self._readings: queue.Queue[SensorReading] = queue.Queue()
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def start(self, on_reading: Callable[[SensorReading], None] | None = None) -> None:
        for index, source in enumerate(self.packet_sources):
            thread = threading.Thread(target=self._source_loop, args=(source, on_reading), name=f"lora-rx-{index}", daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout=2)

    def _source_loop(self, source: Callable[[], Any], on_reading: Callable[[SensorReading], None] | None) -> None:
        while not self._stop.is_set():
            packet = source()
            if packet is None:
                time.sleep(0.05)
                continue
            reading = self.process_packet(packet)
            if reading and on_reading:
                on_reading(reading)

    def receive(self, packet: Any) -> SensorReading | None:
        return self.process_packet(packet)

    def ingest_packet(self, packet: Any) -> SensorReading | None:
        return self.process_packet(packet)

    def process_packet(self, packet: Any) -> SensorReading | None:
        pkt = self._packet_to_dict(packet)
        device_id = str(pkt["device_id"])
        reading_id = str(pkt["reading_id"])
        key = (device_id, reading_id)
        modulus = self._packet_modulus(pkt)
        residue = int(pkt["residue"])

        with self._lock:
            self._expire_locked()
            if key in self._assembled:
                return None
            assembly = self._assemblies.setdefault(key, _Assembly(first_seen=self._clock()))
            assembly.residues[modulus] = residue
            assembly.packets.append(pkt)
            if len(assembly.residues) < 2:
                return None
            value = decode(assembly.residues)
            self._assemblies.pop(key, None)
            self._assembled.add(key)

        reading = SensorReading(
            device_id=device_id,
            reading_id=reading_id,
            value=value,
            zone=pkt.get("zone"),
            timestamp=pkt.get("timestamp"),
            signature=pkt.get("signature"),
            certificate=pkt.get("certificate"),
            residues=dict(assembly.residues),
        )
        self._readings.put(reading)
        return reading

    def next_reading(self, timeout: float | None = None) -> SensorReading | None:
        try:
            return self._readings.get(timeout=timeout)
        except queue.Empty:
            return None

    def expire_incomplete(self) -> None:
        with self._lock:
            self._expire_locked()

    def _expire_locked(self) -> None:
        now = self._clock()
        expired = [key for key, assembly in self._assemblies.items() if now - assembly.first_seen >= self.timeout_seconds]
        for key in expired:
            self._assemblies.pop(key, None)

    @staticmethod
    def _packet_to_dict(packet: Any) -> dict[str, Any]:
        if isinstance(packet, dict):
            return dict(packet)
        if hasattr(packet, "__dict__"):
            return dict(packet.__dict__)
        raise ValueError("packet must be a mapping or object with attributes")

    @staticmethod
    def _packet_modulus(packet: dict[str, Any]) -> int:
        if "modulus" in packet:
            modulus = int(packet["modulus"])
        elif "modulus_index" in packet:
            modulus = MODULI[int(packet["modulus_index"])]
        elif "channel" in packet:
            channel = packet["channel"]
            modulus = MODULI[int(channel)] if isinstance(channel, int) and channel in range(3) else int(channel)
        else:
            raise ValueError("packet must include modulus, modulus_index, or channel")
        if modulus not in MODULI:
            raise ValueError(f"unsupported CRT modulus: {modulus}")
        return modulus
