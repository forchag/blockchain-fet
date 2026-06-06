#include "lora_tx.h"

#include <string.h>

#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define LORA_SPI_HOST SPI2_HOST
#define LORA_PIN_MISO GPIO_NUM_19
#define LORA_PIN_MOSI GPIO_NUM_23
#define LORA_PIN_SCK GPIO_NUM_18
#define LORA_PIN_CS GPIO_NUM_5
#define LORA_PIN_RST GPIO_NUM_14
#define LORA_PIN_DIO0 GPIO_NUM_26

#define REG_FIFO 0x00
#define REG_OP_MODE 0x01
#define REG_FRF_MSB 0x06
#define REG_FRF_MID 0x07
#define REG_FRF_LSB 0x08
#define REG_PA_CONFIG 0x09
#define REG_LNA 0x0C
#define REG_FIFO_ADDR_PTR 0x0D
#define REG_FIFO_TX_BASE_ADDR 0x0E
#define REG_IRQ_FLAGS 0x12
#define REG_MODEM_CONFIG_1 0x1D
#define REG_MODEM_CONFIG_2 0x1E
#define REG_PREAMBLE_MSB 0x20
#define REG_PREAMBLE_LSB 0x21
#define REG_PAYLOAD_LENGTH 0x22
#define REG_MODEM_CONFIG_3 0x26
#define REG_SYNC_WORD 0x39
#define REG_DIO_MAPPING_1 0x40
#define REG_VERSION 0x42

#define MODE_LONG_RANGE_MODE 0x80
#define MODE_SLEEP 0x00
#define MODE_STDBY 0x01
#define MODE_TX 0x03

#define IRQ_TX_DONE_MASK 0x08

static const char *TAG = "lora_tx";
static spi_device_handle_t s_spi;

_Static_assert(sizeof(lora_packet_t) == LORA_PACKET_LEN,
               "unexpected LoRa packet size");

static const uint32_t s_channels_hz[LORA_CHANNEL_COUNT] = {
    868100000u,
    868300000u,
    868500000u,
};

static esp_err_t write_reg(uint8_t reg, uint8_t value) {
  uint8_t tx[2] = {(uint8_t)(reg | 0x80), value};
  spi_transaction_t t = {
      .length = 16,
      .tx_buffer = tx,
  };
  return spi_device_transmit(s_spi, &t);
}

static esp_err_t read_reg(uint8_t reg, uint8_t *value) {
  uint8_t tx[2] = {(uint8_t)(reg & 0x7F), 0};
  uint8_t rx[2] = {0};
  spi_transaction_t t = {
      .length = 16,
      .tx_buffer = tx,
      .rx_buffer = rx,
  };
  esp_err_t err = spi_device_transmit(s_spi, &t);
  if (err == ESP_OK) {
    *value = rx[1];
  }
  return err;
}

static esp_err_t set_frequency(uint32_t hz) {
  const uint64_t frf = ((uint64_t)hz << 19) / 32000000ULL;
  ESP_RETURN_ON_ERROR(write_reg(REG_FRF_MSB, (uint8_t)(frf >> 16)), TAG,
                      "frf msb");
  ESP_RETURN_ON_ERROR(write_reg(REG_FRF_MID, (uint8_t)(frf >> 8)), TAG,
                      "frf mid");
  return write_reg(REG_FRF_LSB, (uint8_t)frf);
}

esp_err_t lora_init(void) {
  spi_bus_config_t buscfg = {
      .miso_io_num = LORA_PIN_MISO,
      .mosi_io_num = LORA_PIN_MOSI,
      .sclk_io_num = LORA_PIN_SCK,
      .quadwp_io_num = -1,
      .quadhd_io_num = -1,
  };
  esp_err_t err = spi_bus_initialize(LORA_SPI_HOST, &buscfg, SPI_DMA_CH_AUTO);
  if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
    return err;
  }

  spi_device_interface_config_t devcfg = {
      .clock_speed_hz = 8 * 1000 * 1000,
      .mode = 0,
      .spics_io_num = LORA_PIN_CS,
      .queue_size = 1,
  };
  err = spi_bus_add_device(LORA_SPI_HOST, &devcfg, &s_spi);
  if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
    return err;
  }

  gpio_set_direction(LORA_PIN_RST, GPIO_MODE_OUTPUT);
  gpio_set_level(LORA_PIN_RST, 0);
  vTaskDelay(pdMS_TO_TICKS(10));
  gpio_set_level(LORA_PIN_RST, 1);
  vTaskDelay(pdMS_TO_TICKS(10));
  gpio_set_direction(LORA_PIN_DIO0, GPIO_MODE_INPUT);

  uint8_t version = 0;
  ESP_RETURN_ON_ERROR(read_reg(REG_VERSION, &version), TAG, "read version");
  if (version != 0x12) {
    ESP_LOGW(TAG, "unexpected SX127x version 0x%02x", version);
  }

  ESP_RETURN_ON_ERROR(write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_SLEEP),
                      TAG, "sleep");
  ESP_RETURN_ON_ERROR(set_frequency(s_channels_hz[0]), TAG, "frequency");
  ESP_RETURN_ON_ERROR(write_reg(REG_FIFO_TX_BASE_ADDR, 0), TAG, "tx base");
  ESP_RETURN_ON_ERROR(write_reg(REG_LNA, 0x23), TAG, "lna");
  ESP_RETURN_ON_ERROR(write_reg(REG_MODEM_CONFIG_1, 0x73), TAG,
                      "bw125 cr45 implicit");
  ESP_RETURN_ON_ERROR(write_reg(REG_MODEM_CONFIG_2, 0x70), TAG, "sf7 crc off");
  ESP_RETURN_ON_ERROR(write_reg(REG_MODEM_CONFIG_3, 0x04), TAG, "agc");
  ESP_RETURN_ON_ERROR(write_reg(REG_PREAMBLE_MSB, 0x00), TAG, "preamble msb");
  ESP_RETURN_ON_ERROR(write_reg(REG_PREAMBLE_LSB, 0x08), TAG, "preamble lsb");
  ESP_RETURN_ON_ERROR(write_reg(REG_PAYLOAD_LENGTH, LORA_PACKET_LEN), TAG,
                      "payload length");
  ESP_RETURN_ON_ERROR(write_reg(REG_SYNC_WORD, 0x34), TAG, "sync word");
  ESP_RETURN_ON_ERROR(write_reg(REG_PA_CONFIG, 0x8F), TAG, "pa config");
  ESP_RETURN_ON_ERROR(write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_STDBY),
                      TAG, "standby");
  return ESP_OK;
}

static esp_err_t transmit_packet(const lora_packet_t *packet,
                                 uint32_t channel_hz) {
  ESP_RETURN_ON_ERROR(write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_STDBY),
                      TAG, "standby");
  ESP_RETURN_ON_ERROR(set_frequency(channel_hz), TAG, "frequency");
  ESP_RETURN_ON_ERROR(write_reg(REG_IRQ_FLAGS, 0xFF), TAG, "clear irq");
  ESP_RETURN_ON_ERROR(write_reg(REG_DIO_MAPPING_1, 0x40), TAG, "dio0 txdone");
  ESP_RETURN_ON_ERROR(write_reg(REG_FIFO_ADDR_PTR, 0), TAG, "fifo ptr");

  const uint8_t *bytes = (const uint8_t *)packet;
  for (size_t i = 0; i < sizeof(*packet); ++i) {
    ESP_RETURN_ON_ERROR(write_reg(REG_FIFO, bytes[i]), TAG, "fifo write");
  }

  ESP_RETURN_ON_ERROR(write_reg(REG_PAYLOAD_LENGTH, sizeof(*packet)), TAG,
                      "payload length");
  ESP_RETURN_ON_ERROR(write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_TX),
                      TAG, "tx");

  const int64_t deadline = esp_timer_get_time() + 2000000LL;
  while (esp_timer_get_time() < deadline) {
    uint8_t flags = 0;
    ESP_RETURN_ON_ERROR(read_reg(REG_IRQ_FLAGS, &flags), TAG, "irq flags");
    if ((flags & IRQ_TX_DONE_MASK) != 0) {
      ESP_RETURN_ON_ERROR(write_reg(REG_IRQ_FLAGS, IRQ_TX_DONE_MASK), TAG,
                          "clear txdone");
      return write_reg(REG_OP_MODE, MODE_LONG_RANGE_MODE | MODE_STDBY);
    }
    vTaskDelay(pdMS_TO_TICKS(10));
  }
  return ESP_ERR_TIMEOUT;
}

esp_err_t
lora_transmit_residue_packets(uint32_t device_id, uint16_t reading_id,
                              const uint8_t residue_values[LORA_CHANNEL_COUNT],
                              const uint8_t signature[SIGNATURE_LEN]) {
  if (residue_values == NULL || signature == NULL) {
    return ESP_ERR_INVALID_ARG;
  }

  for (uint8_t i = 0; i < LORA_CHANNEL_COUNT; ++i) {
    lora_packet_t packet = {
        .device_id = device_id,
        .reading_id = reading_id,
        .residue_index = i,
        .residue_value = residue_values[i],
    };
    memcpy(packet.signature, signature, SIGNATURE_LEN);
    ESP_LOGI(TAG, "transmitting residue %u on %u Hz", i,
             (unsigned)s_channels_hz[i]);
    ESP_RETURN_ON_ERROR(transmit_packet(&packet, s_channels_hz[i]), TAG,
                        "transmit residue");
  }
  return ESP_OK;
}
