#include <inttypes.h>
#include <string.h>
#include <time.h>

#include "cert_store.h"
#include "crt_encode.h"
#include "esp_check.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_random.h"
#include "esp_sleep.h"
#include "esp_sntp.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lora_tx.h"
#include "nvs_flash.h"
#include "sensor.h"
#include "signing.h"

#define SNTP_TIMEOUT_MS 10000u
#define SLEEP_CYCLE_US (30ULL * 60ULL * 1000000ULL)
#define MIN_SLEEP_US (5ULL * 1000000ULL)
#define READING_TEMP_BUCKETS 201u
#define DEVICE_ID_LEN 4u

static const char *TAG = "main";

typedef struct __attribute__((packed)) {
  uint32_t device_id;
  uint16_t reading_id;
  uint16_t soil_moisture_raw;
  int16_t temperature_centi_c;
  int64_t timestamp;
} sensor_payload_t;

static uint32_t device_id_from_mac(void) {
  uint8_t mac[6];
  ESP_ERROR_CHECK(esp_read_mac(mac, ESP_MAC_WIFI_STA));
  uint32_t id = 0;
  memcpy(&id, &mac[2], DEVICE_ID_LEN);
  return id;
}

static bool sync_time(void) {
  esp_sntp_setoperatingmode(SNTP_OPMODE_POLL);
  esp_sntp_setservername(0, "pool.ntp.org");
  esp_sntp_init();

  const int64_t deadline = esp_timer_get_time() + (SNTP_TIMEOUT_MS * 1000LL);
  while (esp_timer_get_time() < deadline) {
    if (esp_sntp_get_sync_status() == SNTP_SYNC_STATUS_COMPLETED) {
      return true;
    }
    vTaskDelay(pdMS_TO_TICKS(250));
  }
  return false;
}

static void enter_enrollment_mode(void) {
  ESP_LOGW(TAG, "certificate expired or missing; entering enrollment mode");
  esp_deep_sleep(MIN_SLEEP_US);
}

static uint32_t encode_sensor_value(const sensor_reading_t *reading) {
  int32_t temp_bucket = ((int32_t)reading->temperature_centi_c + 5500) / 100;
  if (temp_bucket < 0) {
    temp_bucket = 0;
  } else if (temp_bucket >= (int32_t)READING_TEMP_BUCKETS) {
    temp_bucket = READING_TEMP_BUCKETS - 1;
  }

  uint32_t soil = reading->soil_moisture_raw;
  if (soil > 4095) {
    soil = 4095;
  }
  return (soil * READING_TEMP_BUCKETS) + (uint32_t)temp_bucket;
}

void app_main(void) {
  esp_err_t err = nvs_flash_init();
  if (err == ESP_ERR_NVS_NO_FREE_PAGES ||
      err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());
    err = nvs_flash_init();
  }
  ESP_ERROR_CHECK(err);
  ESP_ERROR_CHECK(esp_netif_init());
  ESP_ERROR_CHECK(esp_event_loop_create_default());

  const bool time_synced = sync_time();
  time_t now = 0;
  if (time_synced) {
    time(&now);
    if (cert_store_is_expired(now)) {
      enter_enrollment_mode();
    }
  } else {
    ESP_LOGW(
        TAG,
        "SNTP did not sync within %u ms; skipping certificate expiry check",
        SNTP_TIMEOUT_MS);
  }

  ESP_ERROR_CHECK(sensor_init());
  ESP_ERROR_CHECK(lora_init());

  sensor_reading_t reading = {0};
  ESP_ERROR_CHECK(sensor_read(&reading));

  sensor_payload_t payload = {
      .device_id = device_id_from_mac(),
      .reading_id = (uint16_t)(esp_random() & UINT16_MAX),
      .soil_moisture_raw = reading.soil_moisture_raw,
      .temperature_centi_c = reading.temperature_centi_c,
      .timestamp = time_synced ? (int64_t)now : 0,
  };

  uint8_t signature[SIGNATURE_LEN];
  ESP_ERROR_CHECK(
      sign_sensor_data((const uint8_t *)&payload, sizeof(payload), signature));

  crt_residue_t residues[CRT_RESIDUE_COUNT];
  ESP_ERROR_CHECK(crt_encode(encode_sensor_value(&reading), residues));

  uint8_t residue_values[LORA_CHANNEL_COUNT];
  for (uint8_t i = 0; i < LORA_CHANNEL_COUNT; ++i) {
    residue_values[i] = residues[i].value;
  }
  ESP_ERROR_CHECK(lora_transmit_residue_packets(
      payload.device_id, payload.reading_id, residue_values, signature));

  const uint64_t sleep_us =
      (SLEEP_CYCLE_US < MIN_SLEEP_US) ? MIN_SLEEP_US : SLEEP_CYCLE_US;
  ESP_LOGI(TAG, "sleeping for %" PRIu64 " us", sleep_us);
  esp_deep_sleep(sleep_us);
}
