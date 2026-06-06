#include "cert_store.h"

#include <inttypes.h>
#include <string.h>

#include "esp_attr.h"
#include "esp_efuse.h"
#include "esp_log.h"
#include "esp_rom_crc.h"

static const char *TAG = "cert_store";

RTC_DATA_ATTR static rtc_cert_data_t rtc_cert;

static uint32_t cert_crc32(const rtc_cert_data_t *cert) {
  rtc_cert_data_t tmp = *cert;
  tmp.magic = 0;
  tmp.crc32 = 0;
  return esp_rom_crc32_le(UINT32_MAX, (const uint8_t *)&tmp, sizeof(tmp)) ^
         UINT32_MAX;
}

esp_err_t cert_store_write(const rtc_cert_data_t *cert) {
  if (cert == NULL) {
    return ESP_ERR_INVALID_ARG;
  }

  rtc_cert_data_t tmp = *cert;
  tmp.magic = 0;
  tmp.crc32 = cert_crc32(&tmp);
  tmp.magic = CERT_MAGIC;
  rtc_cert = tmp;
  return ESP_OK;
}

esp_err_t cert_store_read(rtc_cert_data_t *cert) {
  if (cert == NULL) {
    return ESP_ERR_INVALID_ARG;
  }
  if (rtc_cert.magic != CERT_MAGIC) {
    return ESP_ERR_NOT_FOUND;
  }

  const uint32_t expected_crc = rtc_cert.crc32;
  const uint32_t actual_crc = cert_crc32(&rtc_cert);
  if (actual_crc != expected_crc) {
    ESP_LOGW(TAG,
             "RTC certificate CRC mismatch: expected=%08" PRIx32
             " actual=%08" PRIx32,
             expected_crc, actual_crc);
    return ESP_ERR_INVALID_CRC;
  }

  *cert = rtc_cert;
  return ESP_OK;
}

esp_err_t cert_store_get_zone(char *zone, size_t zone_len) {
  if (zone == NULL || zone_len == 0) {
    return ESP_ERR_INVALID_ARG;
  }

  rtc_cert_data_t cert;
  esp_err_t err = cert_store_read(&cert);
  if (err != ESP_OK) {
    return err;
  }

  strlcpy(zone, cert.zone, zone_len);
  return ESP_OK;
}

esp_err_t
cert_store_get_gateway_pubkey(uint8_t pubkey[CERT_GATEWAY_PUBKEY_LEN]) {
  if (pubkey == NULL) {
    return ESP_ERR_INVALID_ARG;
  }

  rtc_cert_data_t cert;
  esp_err_t err = cert_store_read(&cert);
  if (err != ESP_OK) {
    return err;
  }

  memcpy(pubkey, cert.gateway_pubkey, CERT_GATEWAY_PUBKEY_LEN);
  return ESP_OK;
}

bool cert_store_is_expired(time_t now) {
  rtc_cert_data_t cert;
  if (cert_store_read(&cert) != ESP_OK) {
    return true;
  }
  return cert.not_after <= (int64_t)now;
}

esp_err_t private_key_write(const uint8_t key[CERT_PRIVATE_KEY_LEN]) {
  if (key == NULL) {
    return ESP_ERR_INVALID_ARG;
  }

  ESP_LOGW(TAG,
           "Writing the Ed25519 private key to eFuse BLK3 is irreversible");
  return esp_efuse_write_block(EFUSE_BLK3, key, 0, CERT_PRIVATE_KEY_LEN * 8);
}

esp_err_t private_key_read(uint8_t key[CERT_PRIVATE_KEY_LEN]) {
  if (key == NULL) {
    return ESP_ERR_INVALID_ARG;
  }

  memset(key, 0, CERT_PRIVATE_KEY_LEN);
  return esp_efuse_read_block(EFUSE_BLK3, key, 0, CERT_PRIVATE_KEY_LEN * 8);
}
