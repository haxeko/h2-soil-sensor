/*
 * Measurement chain: switch VSENS + battery divider on, wait for the probe peak detector
 * to settle, sample ADC1 (trimmed mean), read the SHT40, switch everything off again.
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
    int      soil_mv;          /* SOIL_ADC voltage (after 1/2 divider), temperature compensated */
    int      soil_mv_raw;      /* uncompensated */
    float    soil_pct;         /* 0..100 % from the dry/wet calibration */

    bool     soil_temp_valid;
    float    soil_temp_c;      /* NTC on the stake */

    bool     vbat_valid;
    int      vbat_mv;
    uint8_t  bat_pct;          /* 0..100 */

    bool     air_valid;
    float    air_temp_c;       /* SHT40 */
    float    air_rh_pct;
} sensor_readings_t;

/** Run one complete measurement (~80 ms awake). Holds a PM lock while running. */
esp_err_t sensors_measure(sensor_readings_t *out);

/** Soil % from a compensated SOIL_ADC voltage and the stored calibration. */
float sensors_soil_percent(int soil_mv);

#ifdef __cplusplus
}
#endif
