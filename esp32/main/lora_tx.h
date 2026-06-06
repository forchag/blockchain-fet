#pragma once

#include <stdint.h>

#include "esp_err.h"
#include "signing.h"

#define LORA_PACKET_LEN 72u
#define LORA_CHANNEL_COUNT 3u

typedef struct __attribute__((packed)) {
  uint32_t device_id;
  uint16_t reading_id;
  uint8_t residue_index;
  uint8_t residue_value;
  uint8_t signature[SIGNATURE_LEN];
} lora_packet_t;

esp_err_t lora_init(void);
esp_err_t
lora_transmit_residue_packets(uint32_t device_id, uint16_t reading_id,
                              const uint8_t residue_values[LORA_CHANNEL_COUNT],
                              const uint8_t signature[SIGNATURE_LEN]);
