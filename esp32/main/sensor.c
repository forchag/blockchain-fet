#include "sensor.h"

#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "sensor";
static adc_oneshot_unit_handle_t s_adc;

static void ow_drive_low(void) {
  gpio_set_direction(DS18B20_GPIO, GPIO_MODE_OUTPUT_OD);
  gpio_set_level(DS18B20_GPIO, 0);
}

static void ow_release(void) {
  gpio_set_direction(DS18B20_GPIO, GPIO_MODE_INPUT_OUTPUT_OD);
  gpio_set_level(DS18B20_GPIO, 1);
}

static bool ow_reset(void) {
  ow_drive_low();
  esp_rom_delay_us(480);
  ow_release();
  esp_rom_delay_us(70);
  const bool present = (gpio_get_level(DS18B20_GPIO) == 0);
  esp_rom_delay_us(410);
  return present;
}

static void ow_write_bit(bool bit) {
  ow_drive_low();
  if (bit) {
    esp_rom_delay_us(6);
    ow_release();
    esp_rom_delay_us(64);
  } else {
    esp_rom_delay_us(60);
    ow_release();
    esp_rom_delay_us(10);
  }
}

static bool ow_read_bit(void) {
  ow_drive_low();
  esp_rom_delay_us(6);
  ow_release();
  esp_rom_delay_us(9);
  const bool bit = gpio_get_level(DS18B20_GPIO) != 0;
  esp_rom_delay_us(55);
  return bit;
}

static void ow_write_byte(uint8_t value) {
  for (int i = 0; i < 8; ++i) {
    ow_write_bit((value & BIT(i)) != 0);
  }
}

static uint8_t ow_read_byte(void) {
  uint8_t value = 0;
  for (int i = 0; i < 8; ++i) {
    if (ow_read_bit()) {
      value |= BIT(i);
    }
  }
  return value;
}

static esp_err_t read_ds18b20(int16_t *temperature_centi_c) {
  if (!ow_reset()) {
    return ESP_ERR_NOT_FOUND;
  }
  ow_write_byte(0xCC); /* Skip ROM. */
  ow_write_byte(0x44); /* Convert T. */
  vTaskDelay(pdMS_TO_TICKS(750));

  if (!ow_reset()) {
    return ESP_ERR_NOT_FOUND;
  }
  ow_write_byte(0xCC); /* Skip ROM. */
  ow_write_byte(0xBE); /* Read scratchpad. */

  const uint8_t lsb = ow_read_byte();
  const uint8_t msb = ow_read_byte();
  const int16_t raw = (int16_t)((msb << 8) | lsb);
  *temperature_centi_c = (int16_t)((raw * 100) / 16);
  return ESP_OK;
}

esp_err_t sensor_init(void) {
  adc_oneshot_unit_init_cfg_t init_cfg = {
      .unit_id = ADC_UNIT_1,
  };
  esp_err_t err = adc_oneshot_new_unit(&init_cfg, &s_adc);
  if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
    return err;
  }

  adc_oneshot_chan_cfg_t chan_cfg = {
      .atten = ADC_ATTEN_DB_11,
      .bitwidth = ADC_BITWIDTH_DEFAULT,
  };
  err = adc_oneshot_config_channel(s_adc, SOIL_ADC_CHANNEL, &chan_cfg);
  if (err != ESP_OK) {
    return err;
  }

  gpio_config_t io_conf = {
      .pin_bit_mask = BIT64(DS18B20_GPIO),
      .mode = GPIO_MODE_INPUT_OUTPUT_OD,
      .pull_up_en = GPIO_PULLUP_ENABLE,
      .pull_down_en = GPIO_PULLDOWN_DISABLE,
      .intr_type = GPIO_INTR_DISABLE,
  };
  return gpio_config(&io_conf);
}

esp_err_t sensor_read(sensor_reading_t *reading) {
  if (reading == NULL) {
    return ESP_ERR_INVALID_ARG;
  }

  int adc_raw = 0;
  esp_err_t err = adc_oneshot_read(s_adc, SOIL_ADC_CHANNEL, &adc_raw);
  if (err != ESP_OK) {
    return err;
  }
  reading->soil_moisture_raw = (uint16_t)adc_raw;

  err = read_ds18b20(&reading->temperature_centi_c);
  if (err != ESP_OK) {
    ESP_LOGW(TAG, "DS18B20 read failed: %s", esp_err_to_name(err));
    return err;
  }
  return ESP_OK;
}
