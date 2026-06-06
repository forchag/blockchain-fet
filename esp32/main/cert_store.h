#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <time.h>

#include "esp_err.h"

#define CERT_MAGIC 0x43455254u /* "CERT" */
#define CERT_ZONE_LEN 16u
#define CERT_GATEWAY_PUBKEY_LEN 32u
#define CERT_PRIVATE_KEY_LEN 32u

typedef struct {
  uint32_t magic;
  uint32_t crc32;
  int64_t not_after;
  char zone[CERT_ZONE_LEN];
  uint8_t gateway_pubkey[CERT_GATEWAY_PUBKEY_LEN];
} rtc_cert_data_t;

esp_err_t cert_store_write(const rtc_cert_data_t *cert);
esp_err_t cert_store_read(rtc_cert_data_t *cert);
esp_err_t cert_store_get_zone(char *zone, size_t zone_len);
esp_err_t
cert_store_get_gateway_pubkey(uint8_t pubkey[CERT_GATEWAY_PUBKEY_LEN]);
bool cert_store_is_expired(time_t now);
esp_err_t private_key_write(const uint8_t key[CERT_PRIVATE_KEY_LEN]);
esp_err_t private_key_read(uint8_t key[CERT_PRIVATE_KEY_LEN]);
