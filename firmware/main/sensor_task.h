#pragma once

#include <stdint.h>
#include "esp_err.h"
#include "sensors.h"

#define SENSOR_REQ_MEASURE  (1u << 0)   /* measure + report now (forces an update) */
#define SENSOR_REQ_CAL_DRY  (1u << 1)   /* store the current reading as the DRY point */
#define SENSOR_REQ_CAL_WET  (1u << 2)   /* store the current reading as the WET point */

esp_err_t sensor_task_start(void);
void sensor_task_request(uint32_t req);

/** Shut down (deep sleep, wake on button) when the battery is below the cut-off. */
void sensor_low_battery_shutdown(int vbat_mv);
