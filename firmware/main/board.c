#include "board.h"

#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_rom_sys.h"

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
    pin_hiz(4);   /* IO4 spare */
    pin_hiz(5);   /* IO5 spare */
    pin_hiz(25);  /* IO25 spare (JTAG strap, ignored with default eFuses) */
    ESP_LOGI(TAG, "board GPIO initialised");
    return ESP_OK;
}

void board_sensor_power(bool on)
{
    if (on) {
#if CONFIG_VSENS_SOFTSTART_US > 0
        /* Soft start: first only the weak internal pull-down (~45 k) works against R9 (100 k),
         * so the Q4 gate slews slowly and the inrush into C7/C14 and the module capacitors
         * is spread out instead of pulling the +3V3 rail down; then drive the gate hard. */
        gpio_config_t c = {
            .pin_bit_mask = 1ULL << BOARD_GPIO_SENS_PWR_EN_N,
            .mode = GPIO_MODE_INPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_ENABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&c);
        esp_rom_delay_us(CONFIG_VSENS_SOFTSTART_US);
#endif
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

void board_hold_power_pins(bool hold)
{
    if (hold) {
        gpio_hold_en(BOARD_GPIO_SENS_PWR_EN_N);
        gpio_hold_en(BOARD_GPIO_VBAT_MEAS_EN);
    } else {
        gpio_hold_dis(BOARD_GPIO_SENS_PWR_EN_N);
        gpio_hold_dis(BOARD_GPIO_VBAT_MEAS_EN);
    }
}
