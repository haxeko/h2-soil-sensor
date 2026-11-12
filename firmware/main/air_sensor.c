#include "air_sensor.h"

#include "driver/i2c_master.h"
#include "esp_check.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sdkconfig.h"

static const char *TAG = "air";
static air_sensor_type_t s_type = AIR_SENSOR_NONE;   /* cached after the first good read */
static uint8_t s_addr;

#define I2C_TIMEOUT_MS 50

static uint8_t crc8(const uint8_t *d, int len)       /* Sensirion & Aosong: x^8+x^5+x^4+1, init 0xFF */
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

static float clamp_rh(float rh)
{
    return rh < 0.0f ? 0.0f : (rh > 100.0f ? 100.0f : rh);
}

/* --------------------------------------------------------------------- SHT4x: 0xFD, 8.3 ms */
static esp_err_t sht4x_read(i2c_master_dev_handle_t dev, float *t, float *rh)
{
    uint8_t cmd = 0xFD, rx[6];
    ESP_RETURN_ON_ERROR(i2c_master_transmit(dev, &cmd, 1, I2C_TIMEOUT_MS), TAG, "sht4x cmd");
    vTaskDelay(pdMS_TO_TICKS(10));
    ESP_RETURN_ON_ERROR(i2c_master_receive(dev, rx, sizeof(rx), I2C_TIMEOUT_MS), TAG, "sht4x read");
    if (crc8(rx, 2) != rx[2] || crc8(rx + 3, 2) != rx[5]) {
        return ESP_ERR_INVALID_CRC;
    }
    *t = -45.0f + 175.0f * (float)((rx[0] << 8) | rx[1]) / 65535.0f;
    *rh = clamp_rh(-6.0f + 125.0f * (float)((rx[3] << 8) | rx[4]) / 65535.0f);
    return ESP_OK;
}

/* ------------------------------------------- SHT3x: single shot, high repeatability, no stretch */
static esp_err_t sht3x_read(i2c_master_dev_handle_t dev, float *t, float *rh)
{
    uint8_t cmd[2] = {0x24, 0x00}, rx[6];
    ESP_RETURN_ON_ERROR(i2c_master_transmit(dev, cmd, 2, I2C_TIMEOUT_MS), TAG, "sht3x cmd");
    vTaskDelay(pdMS_TO_TICKS(16));
    ESP_RETURN_ON_ERROR(i2c_master_receive(dev, rx, sizeof(rx), I2C_TIMEOUT_MS), TAG, "sht3x read");
    if (crc8(rx, 2) != rx[2] || crc8(rx + 3, 2) != rx[5]) {
        return ESP_ERR_INVALID_CRC;
    }
    *t = -45.0f + 175.0f * (float)((rx[0] << 8) | rx[1]) / 65535.0f;
    *rh = clamp_rh(100.0f * (float)((rx[3] << 8) | rx[4]) / 65535.0f);
    return ESP_OK;
}

/* ------------------------------------------------------- AHT20/AHT21: init 0xBE, trigger 0xAC */
static esp_err_t aht20_read(i2c_master_dev_handle_t dev, float *t, float *rh)
{
    uint8_t st = 0, cmd_st = 0x71;
    ESP_RETURN_ON_ERROR(i2c_master_transmit_receive(dev, &cmd_st, 1, &st, 1, I2C_TIMEOUT_MS), TAG, "aht status");
    if (!(st & 0x08)) {                                   /* not calibrated yet: load coefficients */
        uint8_t init[3] = {0xBE, 0x08, 0x00};
        ESP_RETURN_ON_ERROR(i2c_master_transmit(dev, init, 3, I2C_TIMEOUT_MS), TAG, "aht init");
        vTaskDelay(pdMS_TO_TICKS(10));
    }
    uint8_t trig[3] = {0xAC, 0x33, 0x00}, rx[7];
    ESP_RETURN_ON_ERROR(i2c_master_transmit(dev, trig, 3, I2C_TIMEOUT_MS), TAG, "aht trigger");
    vTaskDelay(pdMS_TO_TICKS(80));
    for (int i = 0; i < 5; i++) {
        ESP_RETURN_ON_ERROR(i2c_master_receive(dev, rx, sizeof(rx), I2C_TIMEOUT_MS), TAG, "aht read");
        if (!(rx[0] & 0x80)) {
            break;                                        /* not busy */
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
    if (rx[0] & 0x80) {
        return ESP_ERR_TIMEOUT;
    }
    if (crc8(rx, 6) != rx[6]) {
        return ESP_ERR_INVALID_CRC;
    }
    uint32_t h = ((uint32_t)rx[1] << 12) | ((uint32_t)rx[2] << 4) | (rx[3] >> 4);
    uint32_t tt = (((uint32_t)rx[3] & 0x0F) << 16) | ((uint32_t)rx[4] << 8) | rx[5];
    *rh = clamp_rh((float)h * 100.0f / 1048576.0f);
    *t = (float)tt * 200.0f / 1048576.0f - 50.0f;
    return ESP_OK;
}

static esp_err_t read_type(i2c_master_bus_handle_t bus, air_sensor_type_t type, uint8_t addr, float *t, float *rh)
{
    i2c_master_dev_handle_t dev = NULL;
    i2c_device_config_t dcfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = addr,
        .scl_speed_hz = 100000,
    };
    ESP_RETURN_ON_ERROR(i2c_master_bus_add_device(bus, &dcfg, &dev), TAG, "add device");
    esp_err_t err = ESP_ERR_NOT_SUPPORTED;
    switch (type) {
    case AIR_SENSOR_SHT4X: err = sht4x_read(dev, t, rh); break;
    case AIR_SENSOR_SHT3X: err = sht3x_read(dev, t, rh); break;
    case AIR_SENSOR_AHT20: err = aht20_read(dev, t, rh); break;
    default: break;
    }
    i2c_master_bus_rm_device(dev);
    return err;
}

esp_err_t air_sensor_measure(int sda_gpio, int scl_gpio, float *temp_c, float *rh_pct)
{
    i2c_master_bus_handle_t bus = NULL;
    i2c_master_bus_config_t bcfg = {
        .i2c_port = -1,
        .sda_io_num = sda_gpio,
        .scl_io_num = scl_gpio,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = false,   /* 10k pull-ups to VSENS on the board / module */
    };
    ESP_RETURN_ON_ERROR(i2c_new_master_bus(&bcfg, &bus), TAG, "bus");

    /* candidate list: the cached type first, otherwise what Kconfig allows */
    struct { air_sensor_type_t type; uint8_t addr; } cand[5];
    int n = 0;
    if (s_type != AIR_SENSOR_NONE) {
        cand[n].type = s_type; cand[n++].addr = s_addr;
    } else {
#if CONFIG_SOIL_AIR_SENSOR_AUTO || CONFIG_SOIL_AIR_SENSOR_AHT20
        cand[n].type = AIR_SENSOR_AHT20; cand[n++].addr = 0x38;
#endif
#if CONFIG_SOIL_AIR_SENSOR_AUTO || CONFIG_SOIL_AIR_SENSOR_SHT4X
        cand[n].type = AIR_SENSOR_SHT4X; cand[n++].addr = 0x44;
#endif
#if CONFIG_SOIL_AIR_SENSOR_AUTO || CONFIG_SOIL_AIR_SENSOR_SHT3X
        cand[n].type = AIR_SENSOR_SHT3X; cand[n++].addr = 0x44;
        cand[n].type = AIR_SENSOR_SHT3X; cand[n++].addr = 0x45;
#endif
    }
    esp_err_t err = ESP_ERR_NOT_FOUND;
    for (int i = 0; i < n; i++) {
        if (i2c_master_probe(bus, cand[i].addr, I2C_TIMEOUT_MS) != ESP_OK) {
            continue;
        }
        float t = 0.0f, rh = 0.0f;
        err = read_type(bus, cand[i].type, cand[i].addr, &t, &rh);
        if (err == ESP_OK && t > -40.0f && t < 125.0f) {
            if (s_type != cand[i].type) {
                ESP_LOGI(TAG, "%s found at 0x%02x", air_sensor_name(cand[i].type), cand[i].addr);
            }
            s_type = cand[i].type;
            s_addr = cand[i].addr;
            *temp_c = t;
            *rh_pct = rh;
            break;
        }
    }
    i2c_del_master_bus(bus);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "no air T/RH sensor answered (%s)", esp_err_to_name(err));
    }
    return err;
}

air_sensor_type_t air_sensor_type(void)
{
    return s_type;
}

const char *air_sensor_name(air_sensor_type_t t)
{
    switch (t) {
    case AIR_SENSOR_SHT4X: return "SHT4x";
    case AIR_SENSOR_SHT3X: return "SHT3x";
    case AIR_SENSOR_AHT20: return "AHT20";
    default: return "none";
    }
}
