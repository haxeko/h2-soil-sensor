/*
 * Periodic measurement task. Between measurements the task blocks on a notification
 * with a timeout of one period; with tickless idle + PM the chip spends that time in
 * light sleep while OpenThread keeps polling its parent (SED / ICD slow-poll).
 */
#include "sensor_task.h"

#include <cmath>

#include "app_matter.h"
#include "battery.h"
#include "board.h"
#include "calibration.h"
#include "esp_log.h"
#include "esp_sleep.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "status_led.h"

static const char *TAG = "sensor_task";
static TaskHandle_t s_task;

void sensor_low_battery_shutdown(int vbat_mv)
{
    ESP_LOGW(TAG, "battery %d mV below cut-off %d mV -> shutdown (press the button to retry)", vbat_mv,
             CONFIG_VBAT_SHUTDOWN_MV);
    status_led_set(LED_LOW_BATTERY);
    vTaskDelay(pdMS_TO_TICKS(3000));   /* let the last reports leave the radio */
    board_sensor_power(false);
    board_vbat_divider(false);
    gpio_num_t btn = (gpio_num_t)BOARD_GPIO_BUTTON;
    esp_sleep_enable_ext1_wakeup_io(1ULL << btn, ESP_EXT1_WAKEUP_ANY_LOW);
    esp_deep_sleep_start();
}

static void task(void *arg)
{
    uint32_t req = SENSOR_REQ_MEASURE;   /* first measurement right after boot, forced report */
    int low_count = 0;
    for (;;) {
        sensor_readings_t r;
        sensors_measure(&r);

        if ((req & SENSOR_REQ_CAL_DRY) || (req & SENSOR_REQ_CAL_WET)) {
            bool dry = (req & SENSOR_REQ_CAL_DRY) != 0;
            esp_err_t e = ESP_ERR_INVALID_STATE;
            if (r.soil_mv > 0) {
                e = dry ? calibration_set_dry(r.soil_mv) : calibration_set_wet(r.soil_mv);
            }
            const soil_settings_t *cs = calibration_get();
            bool pair_ok = (cs->dry_mv - cs->wet_mv) >= 50;
            /* error pattern = reading invalid OR pair inconsistent (then calibrate the other point) */
            status_led_set((e == ESP_OK && pair_ok) ? (dry ? LED_CAL_DRY : LED_CAL_WET) : LED_ERROR);
            ESP_LOGI(TAG, "calibration %s at %d mV: %s (dry=%ld wet=%ld)", dry ? "DRY" : "WET", r.soil_mv,
                     esp_err_to_name(e), (long)cs->dry_mv, (long)cs->wet_mv);
            float pct = sensors_soil_percent(r.soil_mv);
            r.soil_valid = r.soil_mv > 0 && !std::isnan(pct);
            r.soil_pct = r.soil_valid ? pct : 0.0f;
        }

        if (r.vbat_valid && CONFIG_VBAT_SHUTDOWN_MV > 0 && r.vbat_mv < CONFIG_VBAT_SHUTDOWN_MV) {
            if (++low_count >= 2) {   /* two consecutive readings: avoid reacting to a TX dip */
                app_matter_publish(&r, true);
                sensor_low_battery_shutdown(r.vbat_mv);
            }
        } else {
            low_count = 0;
        }
        if (r.vbat_valid && (req & SENSOR_REQ_MEASURE) && battery_charge_level(r.bat_pct) == 2) {
            status_led_set(LED_LOW_BATTERY);
        }

        app_matter_publish(&r, req != 0);

        req = 0;
        uint32_t period_ms = calibration_get()->period_s * 1000u;
        xTaskNotifyWait(0, UINT32_MAX, &req, pdMS_TO_TICKS(period_ms));
    }
}

esp_err_t sensor_task_start(void)
{
    BaseType_t ok = xTaskCreate(task, "sensor", 4096, nullptr, 5, &s_task);
    return ok == pdPASS ? ESP_OK : ESP_ERR_NO_MEM;
}

void sensor_task_request(uint32_t req)
{
    if (s_task) {
        xTaskNotify(s_task, req, eSetBits);
    }
}
