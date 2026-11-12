/*
 * Air temperature / humidity from an off-the-shelf I2C module on J6 (VCC GND SCL SDA):
 * Sensirion SHT4x (0x44), Sensirion SHT3x (0x44/0x45) or Aosong AHT20/AHT21 (0x38).
 * The module is powered from VSENS only while measuring, so the bus is created and deleted
 * inside every call and the detected type is cached for the following measurements.
 */
#pragma once

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    AIR_SENSOR_NONE = 0,
    AIR_SENSOR_SHT4X,
    AIR_SENSOR_SHT3X,
    AIR_SENSOR_AHT20,
} air_sensor_type_t;

/**
 * One measurement. VSENS must have been on for >= 40 ms (AHT20 power-up time).
 * Returns ESP_ERR_NOT_FOUND when no supported sensor answers.
 */
esp_err_t air_sensor_measure(int sda_gpio, int scl_gpio, float *temp_c, float *rh_pct);

/** Type found by the last successful measurement (AIR_SENSOR_NONE before that). */
air_sensor_type_t air_sensor_type(void);
const char *air_sensor_name(air_sensor_type_t t);

#ifdef __cplusplus
}
#endif
