#include "board.h"

#include "driver/gpio.h"
#include "driver/ledc.h"
#include "esp_log.h"

static const char *TAG = "board";

static void pin_hiz(int gpio)
{
    gpio_config_t c = {
        .pin_bit_mask = 1ULL << gpio,
        .mode = GPIO_MODE_DISABLE,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&c);
}

static void pin_out(int gpio, int level)
{
    gpio_set_level(gpio, level);
    gpio_config_t c = {
        .pin_bit_mask = 1ULL << gpio,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&c);
    gpio_set_level(gpio, level);
}

esp_err_t board_init(void)
{
    /* R9 pulls SENS_PWR_EN_N high (VSENS off), R6 pulls VBAT_MEAS_EN low (divider off):
     * keep both pins Hi-Z so the resistors define the state, also in light/deep sleep. */
    pin_hiz(BOARD_GPIO_SENS_PWR_EN_N);
    pin_hiz(BOARD_GPIO_VBAT_MEAS_EN);
    board_i2c_release();
    /* LED: output low (off). IO0 is a digital pin, it floats in light sleep -> LED stays off. */
    pin_out(BOARD_GPIO_LED, 0);
    /* unused / analog pins: disable input buffers to avoid shoot-through current */
    pin_hiz(BOARD_GPIO_SOIL_ADC);
    pin_hiz(BOARD_GPIO_VBAT_ADC);
    pin_hiz(BOARD_GPIO_NTC_ADC);
    pin_hiz(BOARD_GPIO_PROBE_EXC);
    pin_hiz(5);   /* IO5 spare */
    pin_hiz(25);  /* IO25 spare (JTAG strap, ignored with default eFuses) */
    ESP_LOGI(TAG, "board GPIO initialised");
    return ESP_OK;
}

void board_sensor_power(bool on)
{
    if (on) {
        pin_out(BOARD_GPIO_SENS_PWR_EN_N, 0);   /* Q4 gate low -> VSENS on */
    } else {
        pin_out(BOARD_GPIO_SENS_PWR_EN_N, 1);   /* drive off quickly ... */
        pin_hiz(BOARD_GPIO_SENS_PWR_EN_N);      /* ... then let R9 hold it */
    }
}

void board_vbat_divider(bool on)
{
    if (on) {
        pin_out(BOARD_GPIO_VBAT_MEAS_EN, 1);
    } else {
        pin_out(BOARD_GPIO_VBAT_MEAS_EN, 0);
        pin_hiz(BOARD_GPIO_VBAT_MEAS_EN);
    }
}

void board_i2c_release(void)
{
    /* SDA/SCL pull-ups sit on VSENS: with VSENS off an internal pull-up would back-feed
     * the rail through R19/R20, so the pins must be inputs without pulls. */
    gpio_reset_pin(BOARD_GPIO_I2C_SDA);   /* note: gpio_reset_pin() enables the pull-up ... */
    gpio_reset_pin(BOARD_GPIO_I2C_SCL);
    pin_hiz(BOARD_GPIO_I2C_SDA);          /* ... so disable everything afterwards */
    pin_hiz(BOARD_GPIO_I2C_SCL);
}

#if CONFIG_SOIL_EXCITATION_LEDC
esp_err_t board_probe_excitation(bool on)
{
    if (!on) {
        ledc_stop(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0);
        pin_hiz(BOARD_GPIO_PROBE_EXC);
        return ESP_OK;
    }
    ledc_timer_config_t t = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = LEDC_TIMER_4_BIT,
        .timer_num = LEDC_TIMER_0,
        .freq_hz = CONFIG_SOIL_EXC_LEDC_FREQ_HZ,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    esp_err_t err = ledc_timer_config(&t);
    if (err != ESP_OK) {
        return err;
    }
    ledc_channel_config_t ch = {
        .gpio_num = BOARD_GPIO_PROBE_EXC,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = LEDC_CHANNEL_0,
        .timer_sel = LEDC_TIMER_0,
        .duty = 8,   /* 50 % of 16 */
        .hpoint = 0,
    };
    return ledc_channel_config(&ch);
}
#else
esp_err_t board_probe_excitation(bool on)
{
    (void)on;
    return ESP_OK;  /* TLC555 runs from VSENS */
}
#endif
