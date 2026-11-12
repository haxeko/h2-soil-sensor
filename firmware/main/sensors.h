/*
 * Measurement chain: switch VSENS on (soft start), light-sleep while the capacitive soil module
 * settles, switch the battery divider on, sample ADC1 (trimmed mean), switch everything off.
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
    int      soil_mv;          /* soil module AOUT (mV) */
    float    soil_pct;         /* 0..100 % from the dry/wet calibration */


    bool     vbat_valid;
    int      vbat_mv;
    uint8_t  bat_pct;          /* 0..100 */

} sensor_readings_t;

/** Run one complete measurement (CONFIG_SOIL_SETTLE_MS in light sleep + ~10 ms awake). */
esp_err_t sensors_measure(sensor_readings_t *out);

/** Soil % from a compensated SOIL_ADC voltage and the stored calibration. */
float sensors_soil_percent(int soil_mv);

#ifdef __cplusplus
}
#endif
