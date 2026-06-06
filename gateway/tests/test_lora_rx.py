from crt_decode import encode
from lora_rx import LoRaReceiver


def test_lora_reassembly_discards_third_residue():
    receiver = LoRaReceiver(clock=lambda: 0)
    residues = encode(4321)
    assert receiver.process_packet({"device_id": "s1", "reading_id": "r1", "modulus": 97, "residue": residues[97], "zone": "North"}) is None
    reading = receiver.process_packet({"device_id": "s1", "reading_id": "r1", "modulus": 101, "residue": residues[101], "zone": "North"})
    assert reading is not None
    assert reading.value == 4321
    assert reading.device_id == "s1"
    assert receiver.process_packet({"device_id": "s1", "reading_id": "r1", "modulus": 103, "residue": residues[103]}) is None


def test_lora_incomplete_timeout():
    now = [0.0]
    receiver = LoRaReceiver(clock=lambda: now[0], timeout_seconds=60)
    residues = encode(12)
    receiver.process_packet({"device_id": "s1", "reading_id": "r2", "modulus": 97, "residue": residues[97]})
    now[0] = 61.0
    receiver.expire_incomplete()
    assert receiver.process_packet({"device_id": "s1", "reading_id": "r2", "modulus": 101, "residue": residues[101]}) is None
