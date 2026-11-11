#include "sht40.h"

#include "driver/i2c_master.h"
#include "esp_check.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "sht40";

#define SHT40_ADDR          0x44
#define SHT40_CMD_MEAS_HIGH 0xFD   /* high repeatability, max 8.3 ms */
#define SHT40_CMD_SOFTRESET 0x94

static uint8_t crc8(const uint8_t *d, int len)
{
    uint8_t crc = 0xFF;
    for (int i = 0; i < len; i++) {
        crc ^= d[i];
        for (int b = 0; b < 8; b++) {
            crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x31) : (uint8_t)(crc << 1);
        }
    }
    return crc;
}

esp_err_t sht40_measure(int sda_gpio, int scl_gpio, float *temp_c, float *rh_pct)
{
    esp_err_t ret = ESP_OK;
    i2c_master_bus_handle_t bus = NULL;
    i2c_master_dev_handle_t dev = NULL;
    i2c_master_bus_config_t bcfg = {
        .i2c_port = -1,
        .sda_io_num = sda_gpio,
        .scl_io_num = scl_gpio,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = false,   /* external 10k pull-ups on VSENS */
    };
    ESP_RETURN_ON_ERROR(i2c_new_master_bus(&bcfg, &bus), TAG, "bus");
    i2c_device_config_t dcfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = SHT40_ADDR,
        .scl_speed_hz = 100000,
    };
    ESP_GOTO_ON_ERROR(i2c_master_bus_add_device(bus, &dcfg, &dev), out, TAG, "device");

    uint8_t cmd = SHT40_CMD_MEAS_HIGH;
    ESP_GOTO_ON_ERROR(i2c_master_transmit(dev, &cmd, 1, 50), out, TAG, "no ACK (sensor missing?)");
    vTaskDelay(pdMS_TO_TICKS(10));
    uint8_t rx[6] = {0};
    ESP_GOTO_ON_ERROR(i2c_master_receive(dev, rx, sizeof(rx), 50), out, TAG, "read");
    if (crc8(rx, 2) != rx[2] || crc8(rx + 3, 2) != rx[5]) {
        ret = ESP_ERR_INVALID_CRC;
        ESP_LOGW(TAG, "CRC error");
        goto out;
    }
    uint16_t t_ticks = (uint16_t)((rx[0] << 8) | rx[1]);
    uint16_t rh_ticks = (uint16_t)((rx[3] << 8) | rx[4]);
    *temp_c = -45.0f + 175.0f * (float)t_ticks / 65535.0f;
    float rh = -6.0f + 125.0f * (float)rh_ticks / 65535.0f;
    *rh_pct = rh < 0.0f ? 0.0f : (rh > 100.0f ? 100.0f : rh);
    ret = ESP_OK;
out:
    if (dev) {
        i2c_master_bus_rm_device(dev);
    }
    if (bus) {
        i2c_del_master_bus(bus);
    }
    return ret;
}
