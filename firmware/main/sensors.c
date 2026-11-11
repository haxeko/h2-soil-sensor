#include "sensors.h"

#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "battery.h"
#include "board.h"
#include "calibration.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_check.h"
#include "esp_log.h"
#include "esp_pm.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sht40.h"

static const char *TAG = "sensors";
static esp_pm_lock_handle_t s_pm_lock;

/* ------------------------------------------------------------------ ADC helpers */
typedef struct {
    int gpio;
    adc_channel_t ch;
    adc_atten_t atten;
    adc_cali_handle_t cali;
} adc_in_t;

static int cmp_int(const void *a, const void *b)
{
    return (*(const int *)a) - (*(const int *)b);
}

static esp_err_t adc_in_setup(adc_oneshot_unit_handle_t unit, adc_in_t *in)
{
    adc_unit_t u;
    ESP_RETURN_ON_ERROR(adc_oneshot_io_to_channel(in->gpio, &u, &in->ch), TAG, "gpio %d is not an ADC pin", in->gpio);
    adc_oneshot_chan_cfg_t cc = { .atten = in->atten, .bitwidth = ADC_BITWIDTH_DEFAULT };
    ESP_RETURN_ON_ERROR(adc_oneshot_config_channel(unit, in->ch, &cc), TAG, "chan");
    adc_cali_curve_fitting_config_t cal = {
        .unit_id = ADC_UNIT_1, .chan = in->ch, .atten = in->atten, .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    if (adc_cali_create_scheme_curve_fitting(&cal, &in->cali) != ESP_OK) {
        in->cali = NULL;
        ESP_LOGW(TAG, "no eFuse ADC calibration, using raw scaling");
    }
    return ESP_OK;
}

/** Trimmed mean of n conversions (drops 1/8 lowest and highest), returned in mV. */
static int adc_read_mv(adc_oneshot_unit_handle_t unit, adc_in_t *in, int n)
{
    int *buf = malloc(sizeof(int) * n);
    if (!buf) {
        return -1;
    }
    int got = 0;
    for (int i = 0; i < n; i++) {
        int raw;
        if (adc_oneshot_read(unit, in->ch, &raw) == ESP_OK) {
            buf[got++] = raw;
        }
    }
    if (got == 0) {
        free(buf);
        return -1;
    }
    qsort(buf, got, sizeof(int), cmp_int);
    int cut = got / 8;
    long sum = 0;
    for (int i = cut; i < got - cut; i++) {
        sum += buf[i];
    }
    int raw = (int)(sum / (got - 2 * cut));
    free(buf);
    int mv = 0;
    if (in->cali && adc_cali_raw_to_voltage(in->cali, raw, &mv) == ESP_OK) {
        return mv;
    }
    /* fallback: nominal full scale per attenuation */
    int fs = in->atten == ADC_ATTEN_DB_12 ? 3300 : (in->atten == ADC_ATTEN_DB_6 ? 1900 : 1000);
    return raw * fs / 4095;
}

/* ------------------------------------------------------------------ conversions */
static float ntc_temp_c(int mv)
{
    /* VSENS -- R18 10k -- NTC_ADC -- RT1 (10k, B3380) -- GND */
    const float vs = (float)CONFIG_NTC_SUPPLY_MV;
    if (mv < 30 || mv > vs - 30) {
        return NAN;   /* open / shorted / not populated */
    }
    float r = 10000.0f * (float)mv / (vs - (float)mv);
    float inv_t = 1.0f / 298.15f + logf(r / 10000.0f) / 3380.0f;
    return 1.0f / inv_t - 273.15f;
}

float sensors_soil_percent(int soil_mv)
{
    int dry = calibration_get()->dry_mv;
    int wet = calibration_get()->wet_mv;
    if (dry - wet < 50) {
        return NAN;   /* invalid calibration */
    }
    float pct = 100.0f * (float)(dry - soil_mv) / (float)(dry - wet);
    return pct < 0.0f ? 0.0f : (pct > 100.0f ? 100.0f : pct);
}

/* ------------------------------------------------------------------ measurement */
esp_err_t sensors_measure(sensor_readings_t *r)
{
    memset(r, 0, sizeof(*r));
    if (!s_pm_lock) {
        ESP_RETURN_ON_ERROR(esp_pm_lock_create(ESP_PM_NO_LIGHT_SLEEP, 0, "sensors", &s_pm_lock), TAG, "pm lock");
    }
    esp_pm_lock_acquire(s_pm_lock);

    board_vbat_divider(true);
    board_sensor_power(true);
    board_probe_excitation(true);
    int64_t t_on = esp_timer_get_time();

#if CONFIG_SOIL_ENABLE_SHT40
    vTaskDelay(pdMS_TO_TICKS(2));   /* SHT40 power-up time 1 ms */
    float at = 0, arh = 0;
    esp_err_t serr = sht40_measure(BOARD_GPIO_I2C_SDA, BOARD_GPIO_I2C_SCL, &at, &arh);
    board_i2c_release();
    if (serr == ESP_OK) {
        r->air_valid = true;
        r->air_temp_c = at;
        r->air_rh_pct = arh;
    }
#endif

    /* wait for the peak detector to settle (TLC555 starts in microseconds) */
    int64_t elapsed_ms = (esp_timer_get_time() - t_on) / 1000;
    if (elapsed_ms < CONFIG_SOIL_SETTLE_MS) {
        vTaskDelay(pdMS_TO_TICKS(CONFIG_SOIL_SETTLE_MS - elapsed_ms));
    }

    adc_oneshot_unit_handle_t unit = NULL;
    adc_oneshot_unit_init_cfg_t ucfg = { .unit_id = ADC_UNIT_1 };
    esp_err_t err = adc_oneshot_new_unit(&ucfg, &unit);
    if (err == ESP_OK) {
        adc_in_t soil = { .gpio = BOARD_GPIO_SOIL_ADC, .atten = ADC_ATTEN_DB_6 };    /* 0..1.9 V */
        adc_in_t vbat = { .gpio = BOARD_GPIO_VBAT_ADC, .atten = ADC_ATTEN_DB_6 };    /* VBAT/2 */
        adc_in_t ntc  = { .gpio = BOARD_GPIO_NTC_ADC,  .atten = ADC_ATTEN_DB_12 };   /* 0..3.3 V */
        adc_in_setup(unit, &soil);
        adc_in_setup(unit, &vbat);
#if CONFIG_SOIL_ENABLE_NTC
        adc_in_setup(unit, &ntc);
#endif
        int n = CONFIG_SOIL_ADC_SAMPLES;
        int soil_mv = adc_read_mv(unit, &soil, n);
        int vb_mv = adc_read_mv(unit, &vbat, n / 2);
#if CONFIG_SOIL_ENABLE_NTC
        int ntc_mv = adc_read_mv(unit, &ntc, n / 2);
        float st = ntc_temp_c(ntc_mv);
        if (!isnan(st) && st > -40.0f && st < 90.0f) {
            r->soil_temp_valid = true;
            r->soil_temp_c = st;
        }
#endif
        if (vb_mv > 0) {
            r->vbat_valid = true;
            r->vbat_mv = vb_mv * CONFIG_VBAT_DIVIDER_RATIO_X1000 / 1000;
            r->bat_pct = battery_percent(r->vbat_mv);
        }
        if (soil_mv > 50) {   /* < 50 mV: oscillator / probe missing */
            r->soil_mv_raw = soil_mv;
            int comp = soil_mv;
            if (r->soil_temp_valid && CONFIG_SOIL_TEMP_COMP_UV_PER_C != 0) {
                comp -= (int)lroundf((float)CONFIG_SOIL_TEMP_COMP_UV_PER_C * (r->soil_temp_c - 25.0f) / 1000.0f);
            }
            r->soil_mv = comp;
            float pct = sensors_soil_percent(comp);
            if (!isnan(pct)) {
                r->soil_valid = true;
                r->soil_pct = pct;
            }
        }
        if (soil.cali) adc_cali_delete_scheme_curve_fitting(soil.cali);
        if (vbat.cali) adc_cali_delete_scheme_curve_fitting(vbat.cali);
        if (ntc.cali) adc_cali_delete_scheme_curve_fitting(ntc.cali);
        adc_oneshot_del_unit(unit);
    } else {
        ESP_LOGE(TAG, "ADC init failed: %s", esp_err_to_name(err));
    }

    board_probe_excitation(false);
    board_sensor_power(false);
    board_vbat_divider(false);
    esp_pm_lock_release(s_pm_lock);

    ESP_LOGI(TAG, "soil %d mV (raw %d) -> %.1f %% | soilT %.2f C | VBAT %d mV (%u %%) | air %.2f C %.1f %%RH%s",
             r->soil_mv, r->soil_mv_raw, r->soil_pct, r->soil_temp_c, r->vbat_mv, r->bat_pct,
             r->air_temp_c, r->air_rh_pct, r->air_valid ? "" : " (no SHT40)");
    return err;
}
