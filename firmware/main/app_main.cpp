/*
 * H2 Soil Sensor - Matter over Thread, battery powered (CR123A), ESP32-H2.
 *
 * Boot sequence
 *   1. NVS, power management (auto light sleep), board GPIO defaults, LED
 *   2. calibration/settings from NVS
 *   3. one measurement BEFORE starting the radio: refuse to boot on an empty battery
 *   4. Matter node + endpoints, esp_matter::start (Thread SED / ICD)
 *   5. button + periodic sensor task
 */
#include <esp_err.h>
#include <esp_log.h>
#include <esp_pm.h>
#include <nvs_flash.h>

#include "app_button.h"
#include "app_matter.h"
#include "board.h"
#include "calibration.h"
#include "sensor_task.h"
#include "sensors.h"
#include "status_led.h"

static const char *TAG = "app_main";

static void init_power_management(void)
{
#if CONFIG_PM_ENABLE
    esp_pm_config_t pm = {
        .max_freq_mhz = CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ,
        .min_freq_mhz = CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ,
#if CONFIG_FREERTOS_USE_TICKLESS_IDLE
        .light_sleep_enable = true,
#endif
    };
    esp_err_t err = esp_pm_configure(&pm);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "esp_pm_configure: %s", esp_err_to_name(err));
    }
#endif
}

extern "C" void app_main(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }
    init_power_management();
    board_init();
    status_led_init();
    calibration_load();

    /* battery check before the radio draws its first 60-140 mA bursts */
    sensor_readings_t r;
    sensors_measure(&r);
    if (r.vbat_valid && CONFIG_VBAT_SHUTDOWN_MV > 0 && r.vbat_mv < CONFIG_VBAT_SHUTDOWN_MV) {
        sensor_low_battery_shutdown(r.vbat_mv);
    }

    if (app_matter_init() != ESP_OK || app_matter_start() != ESP_OK) {
        status_led_set(LED_ERROR);
        ESP_LOGE(TAG, "Matter init failed");
        return;
    }
    app_button_init();
    sensor_task_start();
    if (!app_matter_is_commissioned()) {
        ESP_LOGI(TAG, "not commissioned: BLE commissioning window is open, scan the QR code");
    }
}
