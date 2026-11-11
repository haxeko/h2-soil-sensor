#include "app_button.h"

#include "app_matter.h"
#include "board.h"
#include "button_gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "iot_button.h"
#include "sensor_task.h"
#include "status_led.h"

static const char *TAG = "button";
static bool s_reset_armed;

static void on_single(void *btn, void *data)
{
    ESP_LOGI(TAG, "click: measure now");
    status_led_set(LED_ACK);
    app_matter_user_active_trigger();
    if (!app_matter_is_commissioned()) {
        app_matter_open_commissioning_window();
    }
    sensor_task_request(SENSOR_REQ_MEASURE);
}

static void on_double(void *btn, void *data)
{
    ESP_LOGI(TAG, "double click: calibrate DRY");
    sensor_task_request(SENSOR_REQ_MEASURE | SENSOR_REQ_CAL_DRY);
}

static void on_triple(void *btn, void *data)
{
    ESP_LOGI(TAG, "triple click: calibrate WET");
    sensor_task_request(SENSOR_REQ_MEASURE | SENSOR_REQ_CAL_WET);
}

static void on_hold_3s(void *btn, void *data)
{
    ESP_LOGW(TAG, "hold: keep pressed until 10 s for factory reset");
    s_reset_armed = true;
    status_led_set(LED_HOLD);
}

static void factory_reset_task(void *arg)
{
    status_led_set(LED_FACTORY_RESET);
    vTaskDelay(pdMS_TO_TICKS(600));
    app_matter_factory_reset();   /* does not return */
    vTaskDelete(nullptr);
}

static void on_hold_10s(void *btn, void *data)
{
    ESP_LOGW(TAG, "FACTORY RESET");
    s_reset_armed = false;
    xTaskCreate(factory_reset_task, "freset", 4096, nullptr, 5, nullptr);
}

static void on_release(void *btn, void *data)
{
    if (s_reset_armed) {
        s_reset_armed = false;
        ESP_LOGI(TAG, "factory reset cancelled");
        status_led_set(LED_OFF);
    }
}

esp_err_t app_button_init(void)
{
    button_handle_t h = nullptr;
    const button_config_t cfg = {
        .long_press_time = 3000,
        .short_press_time = 250,
    };
    const button_gpio_config_t gcfg = {
        .gpio_num = BOARD_GPIO_BUTTON,
        .active_level = 0,
        .enable_power_save = true,   /* GPIO wake-up from light sleep, no polling while idle */
        .disable_pull = true,        /* external 10k pull-up R21 */
    };
    esp_err_t err = iot_button_new_gpio_device(&cfg, &gcfg, &h);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "button init failed: %s", esp_err_to_name(err));
        return err;
    }
    iot_button_register_cb(h, BUTTON_SINGLE_CLICK, nullptr, on_single, nullptr);
    iot_button_register_cb(h, BUTTON_DOUBLE_CLICK, nullptr, on_double, nullptr);
    button_event_args_t triple = {};
    triple.multiple_clicks.clicks = 3;
    iot_button_register_cb(h, BUTTON_MULTIPLE_CLICK, &triple, on_triple, nullptr);
    button_event_args_t hold3 = {};
    hold3.long_press.press_time = 3000;
    iot_button_register_cb(h, BUTTON_LONG_PRESS_START, &hold3, on_hold_3s, nullptr);
    button_event_args_t hold10 = {};
    hold10.long_press.press_time = 10000;
    iot_button_register_cb(h, BUTTON_LONG_PRESS_START, &hold10, on_hold_10s, nullptr);
    iot_button_register_cb(h, BUTTON_PRESS_UP, nullptr, on_release, nullptr);
    return ESP_OK;
}
