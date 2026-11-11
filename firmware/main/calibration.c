#include "calibration.h"

#include "esp_check.h"
#include "esp_log.h"
#include "nvs.h"
#include "sdkconfig.h"

static const char *TAG = "calib";
static const char *NS = "soil";

static soil_settings_t s_set = {
    .dry_mv = CONFIG_SOIL_CAL_DRY_MV_DEFAULT,
    .wet_mv = CONFIG_SOIL_CAL_WET_MV_DEFAULT,
    .period_s = CONFIG_SOIL_MEAS_PERIOD_S,
};

esp_err_t calibration_load(void)
{
    nvs_handle_t h;
    esp_err_t err = nvs_open(NS, NVS_READONLY, &h);
    if (err == ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGI(TAG, "no stored settings, defaults: dry=%ld wet=%ld period=%lus",
                 (long)s_set.dry_mv, (long)s_set.wet_mv, (unsigned long)s_set.period_s);
        return ESP_OK;
    }
    ESP_RETURN_ON_ERROR(err, TAG, "nvs_open");
    int32_t v;
    uint32_t u;
    if (nvs_get_i32(h, "dry_mv", &v) == ESP_OK) s_set.dry_mv = v;
    if (nvs_get_i32(h, "wet_mv", &v) == ESP_OK) s_set.wet_mv = v;
    if (nvs_get_u32(h, "period_s", &u) == ESP_OK && u >= 30 && u <= 86400) s_set.period_s = u;
    nvs_close(h);
    ESP_LOGI(TAG, "settings: dry=%ld mV wet=%ld mV period=%lu s",
             (long)s_set.dry_mv, (long)s_set.wet_mv, (unsigned long)s_set.period_s);
    return ESP_OK;
}

const soil_settings_t *calibration_get(void)
{
    return &s_set;
}

static esp_err_t store_i32(const char *key, int32_t v)
{
    nvs_handle_t h;
    ESP_RETURN_ON_ERROR(nvs_open(NS, NVS_READWRITE, &h), TAG, "nvs_open");
    esp_err_t err = nvs_set_i32(h, key, v);
    if (err == ESP_OK) err = nvs_commit(h);
    nvs_close(h);
    return err;
}

/* The two points can be stored in any order; sensors_soil_percent() rejects a pair with
 * (dry - wet) < 50 mV, and the caller signals that state with the error LED pattern. */
esp_err_t calibration_set_dry(int32_t mv)
{
    if (mv < 50 || mv > 3300) {
        return ESP_ERR_INVALID_ARG;
    }
    s_set.dry_mv = mv;
    ESP_LOGI(TAG, "DRY point = %ld mV", (long)mv);
    return store_i32("dry_mv", mv);
}

esp_err_t calibration_set_wet(int32_t mv)
{
    if (mv < 50 || mv > 3300) {
        return ESP_ERR_INVALID_ARG;
    }
    s_set.wet_mv = mv;
    ESP_LOGI(TAG, "WET point = %ld mV", (long)mv);
    return store_i32("wet_mv", mv);
}

esp_err_t calibration_set_period(uint32_t seconds)
{
    if (seconds < 30 || seconds > 86400) {
        return ESP_ERR_INVALID_ARG;
    }
    nvs_handle_t h;
    ESP_RETURN_ON_ERROR(nvs_open(NS, NVS_READWRITE, &h), TAG, "nvs_open");
    esp_err_t err = nvs_set_u32(h, "period_s", seconds);
    if (err == ESP_OK) err = nvs_commit(h);
    nvs_close(h);
    if (err == ESP_OK) s_set.period_s = seconds;
    return err;
}

esp_err_t calibration_reset(void)
{
    nvs_handle_t h;
    ESP_RETURN_ON_ERROR(nvs_open(NS, NVS_READWRITE, &h), TAG, "nvs_open");
    nvs_erase_all(h);
    esp_err_t err = nvs_commit(h);
    nvs_close(h);
    s_set.dry_mv = CONFIG_SOIL_CAL_DRY_MV_DEFAULT;
    s_set.wet_mv = CONFIG_SOIL_CAL_WET_MV_DEFAULT;
    s_set.period_s = CONFIG_SOIL_MEAS_PERIOD_S;
    return err;
}
