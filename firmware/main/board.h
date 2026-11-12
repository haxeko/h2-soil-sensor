/*
 * Board support for the H2 soil sensor (ESP32-H2-WROOM-02C).
 * All power-control signals have external resistors that define the OFF state,
 * so the GPIOs are released to Hi-Z whenever the sensors are not in use.
 */
#pragma once

#include <stdbool.h>
#include "esp_err.h"
#include "sdkconfig.h"

#ifdef __cplusplus
extern "C" {
#endif

#define BOARD_GPIO_SOIL_ADC       CONFIG_GPIO_SOIL_ADC
#define BOARD_GPIO_VBAT_ADC       CONFIG_GPIO_VBAT_ADC
#define BOARD_GPIO_SENS_PWR_EN_N  CONFIG_GPIO_SENS_PWR_EN_N
#define BOARD_GPIO_VBAT_MEAS_EN   CONFIG_GPIO_VBAT_MEAS_EN
#define BOARD_GPIO_LED            CONFIG_GPIO_LED
#define BOARD_GPIO_BUTTON         CONFIG_GPIO_BUTTON

/** Put every board GPIO into its lowest-leakage default state (call once at boot). */
esp_err_t board_init(void);

/** Switch the VSENS rail (capacitive soil module) via Q4, with a soft start. */
void board_sensor_power(bool on);

/** Switch the battery divider (Q2/Q3). */
void board_vbat_divider(bool on);


/**
 * Latch (or release) the current level of the power-control pins so that VSENS / the battery
 * divider keep their state while the CPU light-sleeps during the sensor settling time.
 */
void board_hold_power_pins(bool hold);

#ifdef __cplusplus
}
#endif
