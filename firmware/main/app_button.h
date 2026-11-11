/*
 * BOOT/USER button (IO9, active low, LP GPIO -> wakes the chip from light sleep)
 *   1 click          : measure + report now, ICD active mode; opens the commissioning
 *                      window when the device is not commissioned yet
 *   2 clicks         : store DRY calibration point  (probe in air / dry soil)
 *   3 clicks         : store WET calibration point  (probe in water / saturated soil)
 *   hold >= 3 s      : LED on (warning), release to cancel
 *   hold >= 10 s     : Matter factory reset (calibration is kept)
 */
#pragma once

#include "esp_err.h"

esp_err_t app_button_init(void);
