#pragma once

#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

#define SIGNATURE_LEN 64u
#define SHA256_DIGEST_LEN 32u

esp_err_t sign_sensor_data(const uint8_t *payload, size_t payload_len,
                           uint8_t signature[SIGNATURE_LEN]);
esp_err_t verify_gateway_signature(const uint8_t *payload, size_t payload_len,
                                   const uint8_t signature[SIGNATURE_LEN]);
