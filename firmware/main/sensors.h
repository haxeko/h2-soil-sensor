/*
 * Measurement chain: switch VSENS on, light-sleep while the capacitive soil module settles,
 * read the I2C air sensor, switch the battery divider on, sample ADC1 (trimmed mean),
 * switch everything off again.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    bool     soil_valid;
    int      soil_mv;          /* soil module AOUT (mV), optionally temperature compensated */
    int      soil_mv_raw;      /* uncompensated */
    float    soil_pct;         /* 0..100 % from the dry/wet calibration */

    bool     soil_temp_valid;
    float    soil_temp_c;      /* 10k NTC probe on J7 */

    bool     vbat_valid;
    int      vbat_mv;
    uint8_t  bat_pct;          /* 0..100 */

    bool     air_valid;
    float    air_temp_c;       /* I2C module on J6 (SHT4x / SHT3x / AHT20) */
    float    air_rh_pct;
} sensor_readings_t;

/** Run one complete measurement (CONFIG_SOIL_SETTLE_MS in light sleep + ~30-120 ms awake). */
esp_err_t sensors_measure(sensor_readings_t *out);

/** Soil % from a compensated SOIL_ADC voltage and the stored calibration. */
float sensors_soil_percent(int soil_mv);

#ifdef __cplusplus
}
#endif
