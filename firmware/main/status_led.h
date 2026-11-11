/*
 * Single status LED (IO0, active high). The LED is only driven when there is something
 * to show; a PM lock keeps the chip out of light sleep while a pattern runs because
 * IO0 is a digital pin that floats when the TOP power domain is off.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    LED_OFF = 0,
    LED_ACK,            /* 1 short blink: button press / measurement requested */
    LED_CAL_DRY,        /* 2 blinks: dry point stored */
    LED_CAL_WET,        /* 3 blinks: wet point stored */
    LED_ERROR,          /* 6 fast blinks */
    LED_COMMISSIONING,  /* slow heartbeat while the commissioning window is open */
    LED_IDENTIFY,       /* 1 Hz blink while Identify is active */
    LED_HOLD,           /* steady on: long press in progress (release before 10 s to cancel) */
    LED_FACTORY_RESET,  /* fast blink then off */
    LED_LOW_BATTERY,    /* 3 very short flashes */
} led_pattern_t;

void status_led_init(void);
void status_led_set(led_pattern_t p);

#ifdef __cplusplus
}
#endif
