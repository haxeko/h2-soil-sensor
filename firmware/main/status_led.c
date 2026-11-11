#include "status_led.h"

#include "board.h"
#include "driver/gpio.h"
#include "esp_pm.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

/* pattern = list of on/off durations in ms (even index = on, odd = off) */
typedef struct {
    const uint16_t *steps;
    uint8_t n;
    bool repeat;
} pattern_def_t;

static const uint16_t k_ack[] = {60, 10};
static const uint16_t k_dry[] = {150, 150, 150, 10};
static const uint16_t k_wet[] = {150, 150, 150, 150, 150, 10};
static const uint16_t k_err[] = {50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 10};
static const uint16_t k_comm[] = {40, 1960};
static const uint16_t k_ident[] = {500, 500};
static const uint16_t k_hold[] = {1000};
static const uint16_t k_reset[] = {40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 40, 10};
static const uint16_t k_lowbat[] = {20, 150, 20, 150, 20, 10};

static const pattern_def_t k_patterns[] = {
    [LED_OFF] = {NULL, 0, false},
    [LED_ACK] = {k_ack, 2, false},
    [LED_CAL_DRY] = {k_dry, 4, false},
    [LED_CAL_WET] = {k_wet, 6, false},
    [LED_ERROR] = {k_err, 12, false},
    [LED_COMMISSIONING] = {k_comm, 2, true},
    [LED_IDENTIFY] = {k_ident, 2, true},
    [LED_HOLD] = {k_hold, 1, true},
    [LED_FACTORY_RESET] = {k_reset, 12, false},
    [LED_LOW_BATTERY] = {k_lowbat, 6, false},
};

static esp_timer_handle_t s_timer;
static esp_pm_lock_handle_t s_lock;
static SemaphoreHandle_t s_mutex;
static bool s_locked;
static const pattern_def_t *s_pat;
static uint8_t s_idx;

static void led_write(int on)
{
    gpio_set_level(BOARD_GPIO_LED, on);
}

/* caller holds s_mutex */
static void stop_locked(void)
{
    esp_timer_stop(s_timer);
    led_write(0);
    s_pat = NULL;
    if (s_locked) {
        esp_pm_lock_release(s_lock);   /* never leave the chip awake because of the LED */
        s_locked = false;
    }
}

/* caller holds s_mutex */
static void step_locked(void)
{
    if (!s_pat) {
        return;
    }
    if (s_idx >= s_pat->n) {
        if (!s_pat->repeat) {
            stop_locked();
            return;
        }
        s_idx = 0;
    }
    led_write((s_idx % 2) == 0);
    esp_timer_start_once(s_timer, (uint64_t)s_pat->steps[s_idx] * 1000ULL);
    s_idx++;
}

static void timer_cb(void *arg)
{
    (void)arg;
    xSemaphoreTake(s_mutex, portMAX_DELAY);
    step_locked();
    xSemaphoreGive(s_mutex);
}

void status_led_init(void)
{
    gpio_config_t c = {
        .pin_bit_mask = 1ULL << BOARD_GPIO_LED,
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&c);
    led_write(0);
    s_mutex = xSemaphoreCreateMutex();
    const esp_timer_create_args_t a = {.callback = timer_cb, .name = "led"};
    esp_timer_create(&a, &s_timer);
    esp_pm_lock_create(ESP_PM_NO_LIGHT_SLEEP, 0, "led", &s_lock);
}

void status_led_set(led_pattern_t p)
{
    if (!s_mutex) {
        return;
    }
    xSemaphoreTake(s_mutex, portMAX_DELAY);
    stop_locked();
    if (p != LED_OFF && p < (int)(sizeof(k_patterns) / sizeof(k_patterns[0]))) {
        s_pat = &k_patterns[p];
        s_idx = 0;
        /* IO0 floats when the TOP domain powers down in light sleep, so stay awake
         * for the (short) duration of the pattern. Repeating patterns are only used
         * while the radio is busy anyway (commissioning, identify, button hold). */
        esp_pm_lock_acquire(s_lock);
        s_locked = true;
        step_locked();
    }
    xSemaphoreGive(s_mutex);
}
