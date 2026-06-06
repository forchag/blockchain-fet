#pragma once

#include <stdint.h>

#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_err.h"

#define SOIL_ADC_CHANNEL ADC_CHANNEL_6
#define DS18B20_GPIO GPIO_NUM_4

typedef struct {
  uint16_t soil_moisture_raw;
  int16_t temperature_centi_c;
} sensor_reading_t;

esp_err_t sensor_init(void);
esp_err_t sensor_read(sensor_reading_t *reading);
