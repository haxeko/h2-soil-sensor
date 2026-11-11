#pragma once

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * One-shot high-repeatability measurement on a freshly powered SHT40 (VSENS must be on
 * for >= 1 ms). The I2C bus is created and deleted inside the call so that no I2C
 * peripheral state has to survive light sleep.
 */
esp_err_t sht40_measure(int sda_gpio, int scl_gpio, float *temp_c, float *rh_pct);

#ifdef __cplusplus
}
#endif
