# Design Decisions Log

This log records the implementation decisions made for Parts 10 and 11 and the cross-cutting choices that shaped the firmware, gateway, Fabric network, tests, and documentation.

## Firmware security and enrollment

- **eFuse read protection and key recovery:** the ESP32 Ed25519 private key is written to eFuse block 3 by the firmware key-write path. eFuse programming is irreversible, and production devices should enable eFuse read protection after provisioning so application code can sign with the key but later debug access cannot extract it. There is no key-recovery path after read protection is enabled or after the original key material is lost; recovery means revoking the old certificate, generating a new identity, and reprovisioning or replacing the device. For development, read protection remains a deployment-time action rather than an automatic unit-test action so tests do not permanently alter hardware.
- **eFuse irreversibility warning:** flashing and provisioning instructions must warn operators that burning an incorrect private key or enabling read protection on the wrong device is permanent.
- **Certificate expiry behavior:** firmware checks certificate expiry only after SNTP has synchronized. If the certificate is expired, the device enters enrollment mode instead of transmitting readings under an invalid identity.
- **SNTP failure behavior:** firmware waits up to 10 seconds for SNTP. If synchronization fails, it logs the failure and skips certificate-expiry enforcement for that wake cycle so a temporary time-source outage does not strand sensors in the field.
- **RTC CRC/magic sentinel behavior:** the RTC certificate cache uses both a CRC and a magic sentinel. Writes calculate the CRC before setting the magic value; reads reject missing magic as no cached certificate and reject CRC mismatch as corrupted cached state.
- **Open firmware decision:** the prompt did not require an over-the-air update protocol. Firmware replacement and emergency key rotation therefore remain manual operational processes using the generated flash package and ESP-IDF tooling.

## Sensor encoding and LoRa transport

- **CRT maximum encodable value:** sensor readings are encoded with CRT moduli 97, 101, and 103. The product is `97 × 101 × 103 = 1,009,591`, so values must be in the unambiguous range `0..1,009,590`; values at or above 1,009,591 are rejected before transmission.
- **CRT recovery policy:** gateways may recover a reading from any two distinct residues. This keeps the radio protocol tolerant of one lost residue packet without increasing the sensor payload to a full plaintext reading.
- **LoRa energy/latency trade-off:** the implementation accepts higher latency to reduce energy by changing the radio profile from the faster baseline to the lower-energy profile. The measured energy drops from **24.21mJ to 12.40mJ**, while latency increases from **36.1ms to 94.5ms**. This is the chosen trade-off because battery life is more important than sub-100ms single-reading latency for farm telemetry.
- **Open radio decision:** adaptive data-rate tuning, duty-cycle scheduling across regulatory regions, and link-quality based channel selection were left open by the prompt. The current implementation documents fixed settings and treats regional radio compliance as a deployment responsibility.

## Gateway and policy cache

- **Policy cache TTL:** gateway access decisions are cached for **300 seconds**. This reduces repeated Fabric lookups for stable sensor traffic while bounding stale grant exposure to five minutes under normal connectivity.
- **Policy cache persistence:** cache entries are process-local and are not written to disk. Restarting the gateway clears decisions, and explicit invalidation can remove entries earlier than TTL expiry.
- **CRL propagation/revocation window:** certificate revocations are generated from Fabric CA CRLs and propagated to chaincode. Under connected operation, a gateway can continue using a cached grant for up to the 300-second policy-cache TTL. During connectivity outages, operators must assume a maximum **24-hour CRL window** before all gateways have fetched and applied the latest CRL.
- **Gateway retry behavior:** Fabric invocation retries use bounded exponential backoff with jitter. This keeps short transient failures from immediately failing sensor submissions while avoiding unbounded retry storms.
- **Open gateway decision:** no multi-farm federation or global trust anchor rotation workflow is implemented. Validation is scoped to a single farm MSP and its zones.

## Fabric network and access-control model

- **Fabric topology:** the demonstration network uses one Fabric CA, three Raft orderers, and four peers, one peer per farm zone. Raft was selected because it is the standard Fabric crash-fault-tolerant ordering service for this scale.
- **Raft fault model:** Raft is crash fault tolerant (CFT), not Byzantine fault tolerant (BFT). The design assumes nodes may crash or disconnect but does not defend against malicious orderers equivocation.
- **Role and zone enforcement:** access control is implemented as hierarchical role checks plus zone membership. Sensor and gateway enrollment bind zone attributes into identities, then chaincode decisions combine role, zone, expiry, and nonce checks.
- **Replay protection:** mutating chaincode calls include nonces. Reusing a nonce is rejected so captured submissions cannot be replayed as fresh readings.
- **TLA+ command:** formal access-control checking is run with:

  ```sh
  tlc AccessControl.tla -config AccessControl.cfg -workers 4
  ```

- **Open Fabric decision:** production endorsement policies, HSM-backed CA keys, and cross-organization governance are outside the implementation prompt. The repository keeps a single-farm topology suitable for validation and demonstration.

## Testing and benchmark decisions

- **Security tests:** tests cover unauthorized access, privilege escalation, replay attack rejection, certificate revocation, zone violations, CRT recovery, gateway policy-cache expiry, and enrollment paths.
- **Performance benchmarks:** throughput and latency benchmark scripts include dry-run modes for clean environments and live modes for a bootstrapped Fabric network with the peer CLI available.
- **Benchmark scope:** performance targets are single-farm and hardware/environment dependent. The documentation provides copy-pasteable commands but treats benchmark results as local measurements rather than universal constants.

## Documentation decisions

- **README target:** README commands target a clean Ubuntu 22.04 LTS host.
- **Quick start length:** the README quick start contains exactly five copy-pasteable commands as required.
- **Known limitations:** the README explicitly calls out CFT Raft, the 24-hour CRL window during connectivity outages, and single-farm validation only.

## Benchmark data provenance

- **Benchmark data separation:** Paper-reported benchmark values are stored under `data/benchmarks/`. Live benchmark outputs are stored under `results/`. The project never overwrites paper-reported data with live measurements.
