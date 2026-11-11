/*
 * Persistent settings in NVS (namespace "soil"): probe calibration points and the
 * measurement period. Survives reboots; erased by a Matter factory reset only if the
 * application chooses to (we keep the calibration on purpose, see app_button.cpp).
 */
#pragma once

#include <stdint.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int32_t dry_mv;      /* SOIL_ADC voltage with the probe in air / dry soil (high) */
    int32_t wet_mv;      /* SOIL_ADC voltage with the probe in water / saturated soil (low) */
    uint32_t period_s;   /* measurement period */
} soil_settings_t;

esp_err_t calibration_load(void);
const soil_settings_t *calibration_get(void);
esp_err_t calibration_set_dry(int32_t mv);
esp_err_t calibration_set_wet(int32_t mv);
esp_err_t calibration_set_period(uint32_t seconds);
esp_err_t calibration_reset(void);

#ifdef __cplusplus
}
#endif
