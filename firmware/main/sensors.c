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
static void settle_wait(int64_t t_on_us, int ms)
{
    int64_t left = ms - (esp_timer_get_time() - t_on_us) / 1000;
    if (left <= 0) {
        return;
    }
    /* keep VSENS / divider state latched and let the SoC light-sleep while the module settles */
    board_hold_power_pins(true);
    esp_pm_lock_release(s_pm_lock);
    vTaskDelay(pdMS_TO_TICKS(left));
    esp_pm_lock_acquire(s_pm_lock);
    board_hold_power_pins(false);
}

esp_err_t sensors_measure(sensor_readings_t *r)
{
    memset(r, 0, sizeof(*r));
    if (!s_pm_lock) {
        ESP_RETURN_ON_ERROR(esp_pm_lock_create(ESP_PM_NO_LIGHT_SLEEP, 0, "sensors", &s_pm_lock), TAG, "pm lock");
    }
    esp_pm_lock_acquire(s_pm_lock);

    board_sensor_power(true);
    int64_t t_on = esp_timer_get_time();

    /* capacitive soil module: oscillator + peak detector/RC output need ~1 s to settle */
    settle_wait(t_on, CONFIG_SOIL_SETTLE_MS);
    board_vbat_divider(true);
    vTaskDelay(pdMS_TO_TICKS(3));     /* R7/R8 100k || C6 10 nF: tau = 0.5 ms */

    adc_oneshot_unit_handle_t unit = NULL;
    adc_oneshot_unit_init_cfg_t ucfg = { .unit_id = ADC_UNIT_1 };
    esp_err_t err = adc_oneshot_new_unit(&ucfg, &unit);
    if (err == ESP_OK) {
        adc_in_t soil = { .gpio = BOARD_GPIO_SOIL_ADC, .atten = ADC_ATTEN_DB_12 };   /* AOUT 0..3 V */
        adc_in_t vbat = { .gpio = BOARD_GPIO_VBAT_ADC, .atten = ADC_ATTEN_DB_6 };    /* VBAT/2 */
        adc_in_setup(unit, &soil);
        adc_in_setup(unit, &vbat);
        int n = CONFIG_SOIL_ADC_SAMPLES;
        int soil_mv = adc_read_mv(unit, &soil, n);
        int vb_mv = adc_read_mv(unit, &vbat, n / 2);
        if (vb_mv > 0) {
            r->vbat_valid = true;
            r->vbat_mv = vb_mv * CONFIG_VBAT_DIVIDER_RATIO_X1000 / 1000;
            r->bat_pct = battery_percent(r->vbat_mv);
        }
        if (soil_mv > CONFIG_SOIL_MODULE_MIN_MV) {   /* below: module unplugged or shorted */
            r->soil_mv = soil_mv;
            float pct = sensors_soil_percent(soil_mv);
            if (!isnan(pct)) {
                r->soil_valid = true;
                r->soil_pct = pct;
            }
        }
        if (soil.cali) adc_cali_delete_scheme_curve_fitting(soil.cali);
        if (vbat.cali) adc_cali_delete_scheme_curve_fitting(vbat.cali);
        adc_oneshot_del_unit(unit);
    } else {
        ESP_LOGE(TAG, "ADC init failed: %s", esp_err_to_name(err));
    }

    board_sensor_power(false);
    board_vbat_divider(false);
    esp_pm_lock_release(s_pm_lock);

    ESP_LOGI(TAG, "soil %d mV -> %.1f %%%s | VBAT %d mV (%u %%)", r->soil_mv, r->soil_pct,
             r->soil_valid ? "" : " (module missing?)", r->vbat_mv, r->bat_pct);
    return err;
}
