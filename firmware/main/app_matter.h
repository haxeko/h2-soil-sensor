/*
 * Matter data model of the soil sensor.
 *
 *  EP0  Root Node (+ ICD Management) + Power Source device type
 *       Power Source: Battery + Replaceable, BatVoltage, BatPercentRemaining, BatChargeLevel
 *  EP1  Soil Sensor (0x0045, Matter 1.5): Identify, Soil Measurement (0x0430)
 *  EP2  Humidity Sensor (0x0307): soil moisture mirrored as %RH for ecosystems
 *       that do not support the Soil Sensor device type yet (Apple Home, Google Home)
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"
#include "sensors.h"

esp_err_t app_matter_init(void);          /* node + endpoints, before esp_matter::start() */
esp_err_t app_matter_start(void);         /* esp_matter::start() + post-start configuration */

/** Push readings into the data model, respecting change thresholds / max interval. */
void app_matter_publish(const sensor_readings_t *r, bool force);

bool app_matter_is_commissioned(void);
void app_matter_open_commissioning_window(void);
void app_matter_user_active_trigger(void);   /* ICD: stay in Active Mode (UAT) */
void app_matter_factory_reset(void);
