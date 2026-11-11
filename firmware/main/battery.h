/*
 * CR123A (Li-MnO2, 3.0 V nominal) state-of-charge estimate from the loaded voltage.
 * Li-MnO2 has a flat plateau (~2.9-3.0 V) and a steep knee below ~2.7 V, so the
 * percentage is coarse in the middle and accurate near the end of life.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** 0..100 % from battery millivolts (measured with ~1-2 mA load, sensors on). */
uint8_t battery_percent(int vbat_mv);

/** Matter PowerSource BatChargeLevelEnum: 0 = OK, 1 = Warning, 2 = Critical. */
uint8_t battery_charge_level(uint8_t pct);

/** True when the battery should be replaced (<= 10 %). */
bool battery_replacement_needed(uint8_t pct);

#ifdef __cplusplus
}
#endif
